"""Ubicación con Nominatim (OpenStreetMap): dirección -> coordenadas y coordenadas -> calle y colonia.

Cuidados que pide la política de uso de Nominatim (DISENO_TECNICO, sección 6):
- User-Agent genérico del proyecto (nunca un correo ni datos personales).
- Máximo 1 petición por segundo: un candado y la hora de la última petición hacen esperar a la siguiente.
- Caché en memoria: la misma búsqueda no se repite durante GEO_CACHE_MIN minutos.
- Tiempo de espera de 5 s. Si Nominatim falla o tarda, la API responde 503 SERVICIO_NO_DISPONIBLE y el
  frontend deja capturar la ubicación a mano.

La colonia se asigna comparando el nombre que devuelve Nominatim con NUESTRO catálogo (sin distinguir
mayúsculas ni acentos). Si no coincide, colonia_id queda en null y la persona la elige en una lista.

En las pruebas NUNCA se llama a la red: se reemplaza la función _llamar_http (ver tests/test_geo.py).
"""

import threading
import time
import unicodedata

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errores import ErrorApi, error_validacion
from app.core.geo import dentro_del_municipio
from app.core.reglas import (
    GEO_BUSQUEDA_MIN,
    GEO_CACHE_MIN,
    GEO_INTERVALO_MIN_S,
    GEO_MAX_RESULTADOS,
    GEO_TIEMPO_ESPERA_S,
    MUNICIPIO_BBOX,
)
from app.models import Colonia
from app.schemas.geo import GeoResultado

URL_NOMINATIM = "https://nominatim.openstreetmap.org"
USER_AGENT = "LiebreUrbana-proyecto-escolar"

# Llaves de "address" de Nominatim donde puede venir el nombre de la colonia, de la más a la menos precisa
LLAVES_COLONIA = ("suburb", "neighbourhood", "quarter", "city_district")
LLAVES_CALLE = ("road", "pedestrian", "residential", "footway")

# --- Estado en memoria (uno por proceso del servidor) ---------------------------------------------
_candado = threading.Lock()
_ultima_peticion: float | None = None  # time.monotonic() de la última llamada real a Nominatim
_cache: dict[tuple, tuple[float, object]] = {}  # llave -> (momento en que vence, respuesta de Nominatim)

# Se guardan en variables para que las pruebas puedan simular el reloj y la espera sin dormir de verdad
_reloj = time.monotonic
_dormir = time.sleep


def limpiar_estado() -> None:
    """Vacía la caché y olvida la última petición (lo usan las pruebas)."""
    global _ultima_peticion
    _cache.clear()
    _ultima_peticion = None


def _llamar_http(ruta: str, parametros: dict) -> object:
    """La ÚNICA función que sale a internet. Devuelve el JSON de Nominatim o lanza un error de httpx."""
    respuesta = httpx.get(
        f"{URL_NOMINATIM}/{ruta}",
        params=parametros,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "es"},
        timeout=GEO_TIEMPO_ESPERA_S,
    )
    respuesta.raise_for_status()
    return respuesta.json()


def _consultar(ruta: str, parametros: dict) -> object:
    """Consulta Nominatim respetando la caché y el límite de 1 petición por segundo."""
    global _ultima_peticion
    llave = (ruta, tuple(sorted(parametros.items())))
    with _candado:
        guardado = _cache.get(llave)
        if guardado and guardado[0] > _reloj():
            return guardado[1]

        # Límite de ritmo: si la petición anterior fue hace menos de 1 s, se espera lo que falte
        if _ultima_peticion is not None:
            falta = GEO_INTERVALO_MIN_S - (_reloj() - _ultima_peticion)
            if falta > 0:
                _dormir(falta)
        _ultima_peticion = _reloj()
        try:
            datos = _llamar_http(ruta, parametros)
        except (httpx.HTTPError, ValueError):
            # ValueError: Nominatim respondió algo que no es JSON. En ambos casos no hay datos confiables.
            raise ErrorApi(
                503,
                "SERVICIO_NO_DISPONIBLE",
                "El servicio de mapas no responde. Intenta más tarde o captura la ubicación a mano",
            ) from None

        _cache[llave] = (_reloj() + GEO_CACHE_MIN * 60, datos)
        return datos


# --- Colonia: comparar nombres sin mayúsculas ni acentos -------------------------------------------
def normalizar_nombre(texto: str) -> str:
    """'Col. Partido  ESCOBEDO' y 'partido escobedo' quedan igual: sin acentos, minúsculas, sin "colonia"."""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    palabras = sin_acentos.lower().replace(".", " ").split()
    if palabras and palabras[0] in ("colonia", "col", "fraccionamiento", "fracc"):
        palabras = palabras[1:]
    return " ".join(palabras)


def buscar_colonia(db: Session, direccion: dict) -> Colonia | None:
    """Busca en el catálogo (solo activas) la colonia que nombra Nominatim en `address`."""
    candidatos = [normalizar_nombre(direccion[llave]) for llave in LLAVES_COLONIA if direccion.get(llave)]
    if not candidatos:
        return None
    # El catálogo de Juárez tiene cientos de colonias, no millones: compararlas en Python es simple y suficiente
    por_nombre = {normalizar_nombre(c.nombre): c for c in db.scalars(select(Colonia).where(Colonia.activa.is_(True)))}
    for candidato in candidatos:
        if candidato in por_nombre:
            return por_nombre[candidato]
    return None


def _a_resultado(db: Session, lugar: dict, punto: tuple[float, float] | None = None) -> GeoResultado:
    """Convierte un lugar de Nominatim (formato jsonv2) en un GeoResultado del contrato.

    `punto` conserva las coordenadas que mandó la persona (búsqueda inversa): son más precisas que el centro
    de la calle que devuelve Nominatim.
    """
    direccion = lugar.get("address") or {}
    lat, lon = punto if punto else (float(lugar["lat"]), float(lugar["lon"]))
    calle = next((direccion[llave] for llave in LLAVES_CALLE if direccion.get(llave)), None)
    colonia = buscar_colonia(db, direccion)
    return GeoResultado(
        etiqueta=lugar.get("display_name") or f"{lat}, {lon}",
        lat=lat,
        lon=lon,
        calle=calle,
        colonia_id=colonia.id if colonia else None,
        colonia_nombre=colonia.nombre if colonia else None,
        dentro_del_municipio=dentro_del_municipio(lat, lon),
    )


# --- Funciones que usan los routers ----------------------------------------------------------------
def buscar(db: Session, q: str) -> list[GeoResultado]:
    """Dirección -> hasta 5 lugares DENTRO del rectángulo de Juárez. Lista vacía si no hay coincidencias."""
    texto = " ".join((q or "").split())
    if len(texto) < GEO_BUSQUEDA_MIN:
        raise error_validacion({"q": f"Escribe al menos {GEO_BUSQUEDA_MIN} caracteres de la dirección"})
    lat_min, lat_max, lon_min, lon_max = MUNICIPIO_BBOX
    parametros = {
        "q": texto,
        "format": "jsonv2",
        "addressdetails": 1,
        "countrycodes": "mx",
        "limit": GEO_MAX_RESULTADOS,
        # viewbox = izquierda,arriba,derecha,abajo; bounded=1 descarta lo que quede fuera del rectángulo
        "viewbox": f"{lon_min},{lat_max},{lon_max},{lat_min}",
        "bounded": 1,
    }
    lugares = _consultar("search", parametros)
    if not isinstance(lugares, list):
        return []
    return [_a_resultado(db, lugar) for lugar in lugares[:GEO_MAX_RESULTADOS]]


def inversa(db: Session, lat: float, lon: float) -> GeoResultado:
    """Coordenadas -> calle y colonia.

    Si Nominatim no encuentra nada en ese punto (responde {"error": ...}), se devuelve el mismo punto sin calle
    ni colonia: la persona las escribe o elige a mano. No es un error porque la ubicación sí es válida.
    """
    parametros = {"lat": round(lat, 6), "lon": round(lon, 6), "format": "jsonv2", "addressdetails": 1, "zoom": 18}
    lugar = _consultar("reverse", parametros)
    if not isinstance(lugar, dict) or "lat" not in lugar or "error" in lugar:
        return GeoResultado(
            etiqueta=f"{lat}, {lon}",
            lat=lat,
            lon=lon,
            calle=None,
            colonia_id=None,
            colonia_nombre=None,
            dentro_del_municipio=dentro_del_municipio(lat, lon),
        )
    return _a_resultado(db, lugar, punto=(lat, lon))
