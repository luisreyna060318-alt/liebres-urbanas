"""Aviso de lluvia con Open-Meteo (HU-08.1). No necesita llave.

Qué hace: pide la probabilidad de precipitación POR HORA para un punto céntrico de Ciudad Juárez y toma la
MÁXIMA de las próximas HORAS_PRONOSTICO (12) horas, empezando por la hora actual. Si esa máxima llega al
UMBRAL_LLUVIA_PCT (30 %), hay aviso.

Cuidados (DISENO_TECNICO, sección 6):
- Caché en memoria de CACHE_PRONOSTICO_HORAS (1 h): el pronóstico no cambia por cada visita a la página.
- Tiempo de espera con tope por fase (TIEMPO_ESPERA, ver abajo). Si Open-Meteo falla, tarda o responde algo
  inválido, NO se levanta un error: la respuesta es 200 con disponible=false y la interfaz muestra
  "Pronóstico no disponible" (CA4).
- Un fallo solo se recuerda unos segundos (CACHE_FALLO_S): así no se queda la plataforma "sin pronóstico" una
  hora entera por un tropiezo de red, pero tampoco se espera el tiempo límite en cada visita mientras el
  servicio está caído.
- User-Agent genérico del proyecto: nunca un correo ni datos personales.

En las pruebas NUNCA se llama a la red: se reemplaza la función _llamar_http y el reloj _reloj (tests/test_clima.py).
"""

import threading
from datetime import datetime, timedelta

import httpx

from app.core.reglas import CACHE_PRONOSTICO_HORAS, HORAS_PRONOSTICO, UMBRAL_LLUVIA_PCT, ZONA_HORARIA
from app.core.tiempo import ZONA_JUAREZ, ahora_utc, como_utc
from app.schemas.clima import AvisoLluvia

URL_OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "LiebreUrbana-proyecto-escolar"
# httpx mide el tiempo de espera POR FASE, no en total: un solo número (timeout=5) permitiría 5 s para conectar,
# otros 5 para enviar, 5 por cada lectura y 5 esperando conexión libre. Por eso se fija cada fase por separado.
# La respuesta de Open-Meteo es pequeña (unos KB: una o dos lecturas), así que en la práctica la consulta completa
# no pasa de unos 10 s (2 + 2 + 5 + 1). Sin un tope total de httpx, solo un servidor que mandara los datos gota a
# gota podría alargarla; aun así cualquier fallo o espera vencida termina en disponible=false, nunca en un error.
# Mientras dura la consulta se mantiene el candado (ver obtener_aviso), así que las visitas que llegan a la vez
# esperan, como mucho, este mismo tiempo y luego leen la caché que dejó la primera.
TIEMPO_CONECTAR_S = 2  # abrir la conexión con Open-Meteo
TIEMPO_ESCRIBIR_S = 2  # enviar la petición
TIEMPO_LEER_S = 5  # esperar cada parte de la respuesta
TIEMPO_POOL_S = 1  # esperar una conexión libre del cliente
TIEMPO_ESPERA = httpx.Timeout(
    connect=TIEMPO_CONECTAR_S, read=TIEMPO_LEER_S, write=TIEMPO_ESCRIBIR_S, pool=TIEMPO_POOL_S
)
CACHE_FALLO_S = 30  # un fallo se recuerda solo este tiempo

# Punto fijo para todo el pronóstico: el Centro de Ciudad Juárez (cerca de la Misión de Guadalupe), redondeado a
# 2 decimales. Open-Meteo calcula el pronóstico sobre una malla de varios kilómetros, así que no hace falta más
# precisión, y un solo punto da una sola consulta (y una sola caché) para toda la ciudad.
LATITUD = 31.74
LONGITUD = -106.49

# --- Estado en memoria (uno por proceso del servidor) ---------------------------------------------
_candado = threading.Lock()
_cache: tuple[datetime, AvisoLluvia] | None = None  # (momento en que vence, resultado)

# Se guarda en una variable para que las pruebas puedan simular el paso del tiempo
_reloj = ahora_utc


def limpiar_estado() -> None:
    """Vacía la caché (lo usan las pruebas)."""
    global _cache
    _cache = None


def _llamar_http(parametros: dict) -> object:
    """La ÚNICA función que sale a internet. Devuelve el JSON de Open-Meteo o lanza un error de httpx."""
    respuesta = httpx.get(
        URL_OPEN_METEO,
        params=parametros,
        headers={"User-Agent": USER_AGENT},
        timeout=TIEMPO_ESPERA,
    )
    respuesta.raise_for_status()
    return respuesta.json()


def _sin_pronostico() -> AvisoLluvia:
    return AvisoLluvia(
        disponible=False,
        hay_aviso=False,
        probabilidad_max_pct=None,
        horas=HORAS_PRONOSTICO,
        umbral_pct=UMBRAL_LLUVIA_PCT,
        consultado_en=None,
    )


def _maxima_proxima_horas(datos: object, ahora: datetime) -> int | None:
    """La probabilidad máxima de las próximas 12 h, o None si la respuesta no sirve.

    Open-Meteo devuelve {"hourly": {"time": ["2026-11-25T14:00", ...], "precipitation_probability": [20, ...]}}
    con las horas en la zona pedida (la de Juárez). La ventana va de la hora en punto actual (la hora en curso
    cuenta) hasta 12 horas después: no se mira el pasado ni lo que queda más allá.
    """
    if not isinstance(datos, dict) or not isinstance(datos.get("hourly"), dict):
        return None
    horas = datos["hourly"].get("time")
    probabilidades = datos["hourly"].get("precipitation_probability")
    if not isinstance(horas, list) or not isinstance(probabilidades, list) or len(horas) != len(probabilidades):
        return None

    inicio = como_utc(ahora.astimezone(ZONA_JUAREZ).replace(minute=0, second=0, microsecond=0))
    fin = inicio + timedelta(hours=HORAS_PRONOSTICO)

    en_ventana: list[float] = []
    for texto, valor in zip(horas, probabilidades, strict=True):
        try:
            hora = como_utc(datetime.fromisoformat(texto).replace(tzinfo=ZONA_JUAREZ))
        except (TypeError, ValueError):
            return None  # una hora que no se entiende: no se puede confiar en el resto
        if not inicio <= hora < fin:
            continue
        if valor is None:
            continue  # Open-Meteo puede dejar horas sin dato
        if isinstance(valor, bool) or not isinstance(valor, int | float) or not 0 <= valor <= 100:
            return None
        en_ventana.append(valor)

    return round(max(en_ventana)) if en_ventana else None


def _consultar(ahora: datetime) -> AvisoLluvia:
    """Pide el pronóstico a Open-Meteo y arma la respuesta. Cualquier problema -> sin pronóstico."""
    parametros = {
        "latitude": LATITUD,
        "longitude": LONGITUD,
        "hourly": "precipitation_probability",
        "timezone": ZONA_HORARIA,
        "forecast_days": 2,  # con 1 día, a las 20:00 no alcanzarían las 12 horas siguientes
    }
    try:
        datos = _llamar_http(parametros)
    except (httpx.HTTPError, ValueError):
        # ValueError: Open-Meteo respondió algo que no es JSON
        return _sin_pronostico()

    maxima = _maxima_proxima_horas(datos, ahora)
    if maxima is None:
        return _sin_pronostico()
    return AvisoLluvia(
        disponible=True,
        hay_aviso=maxima >= UMBRAL_LLUVIA_PCT,
        probabilidad_max_pct=maxima,
        horas=HORAS_PRONOSTICO,
        umbral_pct=UMBRAL_LLUVIA_PCT,
        consultado_en=ahora,
    )


def _de_la_cache(ahora: datetime) -> AvisoLluvia | None:
    return _cache[1] if _cache and _cache[0] > ahora else None


def obtener_aviso() -> AvisoLluvia:
    """Lo que usa el router: responde de la caché si sigue vigente; si no, consulta a Open-Meteo."""
    global _cache
    guardado = _de_la_cache(_reloj())
    if guardado:
        return guardado

    # Un candado evita que varias visitas a la vez lancen cada una su propia consulta a internet
    with _candado:
        ahora = _reloj()
        guardado = _de_la_cache(ahora)  # otra petición pudo traerla mientras esperábamos
        if guardado:
            return guardado

        resultado = _consultar(ahora)
        vigencia = timedelta(hours=CACHE_PRONOSTICO_HORAS) if resultado.disponible else timedelta(seconds=CACHE_FALLO_S)
        _cache = (ahora + vigencia, resultado)
        return resultado
