"""Aviso de lluvia (HU-08.1). La red SIEMPRE se simula: ninguna prueba sale a internet."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.core.geo import dentro_del_municipio
from app.core.reglas import CACHE_PRONOSTICO_HORAS, HORAS_PRONOSTICO, UMBRAL_LLUVIA_PCT
from app.services import clima

# 14:30 en Ciudad Juárez (en noviembre es UTC-7): la ventana de 12 h va de las 14:00 a las 02:00 del día siguiente
AHORA = datetime(2026, 11, 25, 21, 30, tzinfo=UTC)
URL = "/api/clima/aviso"
LLAMAR_HTTP_REAL = clima._llamar_http  # la fixture automática lo reemplaza en cada prueba


def pronostico(**por_hora: int | None) -> dict:
    """Respuesta de Open-Meteo con 48 horas (25 y 26 de noviembre) en 0 %. `por_hora` ajusta horas concretas:
    pronostico(**{"2026-11-25T16:00": 45}) o, más corto, pronostico(h25_16=45) / pronostico(h26_01=45)."""
    inicio = datetime(2026, 11, 25)
    horas = [(inicio + timedelta(hours=n)).strftime("%Y-%m-%dT%H:%M") for n in range(48)]
    valores: list[int | None] = [0] * 48
    for llave, valor in por_hora.items():
        dia, hora = llave[1:].split("_")  # "h25_16" -> día 25, hora 16
        valores[(int(dia) - 25) * 24 + int(hora)] = valor
    return {"hourly": {"time": horas, "precipitation_probability": valores}}


class OpenMeteoFalso:
    """Reemplaza a clima._llamar_http: responde lo que se le indique y anota cada llamada."""

    def __init__(self, respuesta=None, error: Exception | None = None):
        self.respuesta = respuesta
        self.error = error
        self.llamadas: list[dict] = []

    def __call__(self, parametros):
        self.llamadas.append(parametros)
        if self.error:
            raise self.error
        return self.respuesta


@pytest.fixture(autouse=True)
def sin_red_clima(monkeypatch):
    """Cada prueba empieza con caché vacía y, si no instala un Open-Meteo falso, no puede salir a internet."""

    def _prohibido(parametros):
        raise AssertionError("Prueba sin simular la red: se intentó llamar a Open-Meteo")

    clima.limpiar_estado()
    monkeypatch.setattr(clima, "_llamar_http", _prohibido)
    yield
    clima.limpiar_estado()


@pytest.fixture()
def open_meteo(monkeypatch):
    """Instala un Open-Meteo falso (pronóstico sin lluvia por omisión); la prueba ajusta .respuesta o .error."""
    falso = OpenMeteoFalso(respuesta=pronostico())
    monkeypatch.setattr(clima, "_llamar_http", falso)
    return falso


@pytest.fixture()
def reloj(monkeypatch):
    """Reloj simulado: la prueba mueve reloj["ahora"] para avanzar el tiempo."""
    estado = {"ahora": AHORA}
    monkeypatch.setattr(clima, "_reloj", lambda: estado["ahora"])
    return estado


# --- Umbral -----------------------------------------------------------------------------------------
def test_umbral_viene_de_las_reglas():
    assert (UMBRAL_LLUVIA_PCT, HORAS_PRONOSTICO, CACHE_PRONOSTICO_HORAS) == (30, 12, 1)


def test_29_por_ciento_no_avisa(client, open_meteo, reloj):
    open_meteo.respuesta = pronostico(h25_18=29)
    r = client.get(URL)
    assert r.status_code == 200
    assert r.json() == {
        "disponible": True,
        "hay_aviso": False,
        "probabilidad_max_pct": 29,
        "horas": 12,
        "umbral_pct": 30,
        "consultado_en": "2026-11-25T21:30:00Z",
    }


def test_30_por_ciento_si_avisa(client, open_meteo, reloj):
    open_meteo.respuesta = pronostico(h25_18=30)
    cuerpo = client.get(URL).json()
    assert cuerpo["disponible"] is True and cuerpo["hay_aviso"] is True
    assert cuerpo["probabilidad_max_pct"] == 30


def test_sin_lluvia_no_hay_aviso(client, open_meteo, reloj):
    cuerpo = client.get(URL).json()
    assert cuerpo["disponible"] is True and cuerpo["hay_aviso"] is False
    assert cuerpo["probabilidad_max_pct"] == 0


def test_toma_la_maxima_de_la_ventana(client, open_meteo, reloj):
    open_meteo.respuesta = pronostico(h25_15=20, h25_19=45, h25_23=10)
    assert client.get(URL).json()["probabilidad_max_pct"] == 45


# --- Ventana de 12 horas ---------------------------------------------------------------------------
def test_ignora_las_horas_pasadas(client, open_meteo, reloj):
    # 13:00 ya pasó (son las 14:30): su 90 % no cuenta
    open_meteo.respuesta = pronostico(h25_13=90, h25_00=80, h25_17=10)
    cuerpo = client.get(URL).json()
    assert cuerpo["probabilidad_max_pct"] == 10 and cuerpo["hay_aviso"] is False


def test_la_hora_en_curso_si_cuenta(client, open_meteo, reloj):
    open_meteo.respuesta = pronostico(h25_14=50)  # son las 14:30: la franja de las 14:00 sigue vigente
    cuerpo = client.get(URL).json()
    assert cuerpo["probabilidad_max_pct"] == 50 and cuerpo["hay_aviso"] is True


def test_ignora_lo_que_queda_despues_de_12_horas(client, open_meteo, reloj):
    # La última hora de la ventana es la 01:00 del día 26; las 02:00 ya quedan fuera
    open_meteo.respuesta = pronostico(h26_01=35, h26_02=95, h26_10=95)
    cuerpo = client.get(URL).json()
    assert cuerpo["probabilidad_max_pct"] == 35

    clima.limpiar_estado()
    open_meteo.respuesta = pronostico(h26_02=95, h26_10=95)
    cuerpo = client.get(URL).json()
    assert cuerpo["probabilidad_max_pct"] == 0 and cuerpo["hay_aviso"] is False


def test_las_horas_se_leen_en_la_zona_de_juarez(client, open_meteo, reloj):
    # A las 21:30 UTC del 25 son las 14:30 en Juárez; si se confundieran las zonas, la 01:00 del 26 quedaría fuera
    open_meteo.respuesta = pronostico(h26_01=60)
    assert client.get(URL).json()["probabilidad_max_pct"] == 60


def test_horas_sin_dato_se_saltan(client, open_meteo, reloj):
    open_meteo.respuesta = pronostico(h25_15=None, h25_16=40)
    assert client.get(URL).json()["probabilidad_max_pct"] == 40


# --- Qué se le pregunta a Open-Meteo -----------------------------------------------------------------
def test_pide_probabilidad_por_hora_para_juarez(client, open_meteo, reloj):
    client.get(URL)
    parametros = open_meteo.llamadas[0]
    assert parametros["hourly"] == "precipitation_probability"
    assert parametros["timezone"] == "America/Ciudad_Juarez"
    assert parametros["forecast_days"] == 2
    assert dentro_del_municipio(parametros["latitude"], parametros["longitude"])
    assert "apikey" not in parametros  # Open-Meteo no necesita llave


def test_llamada_real_con_user_agent_generico_y_5_segundos(monkeypatch):
    """_llamar_http es la única función que sale a internet; aquí se reemplaza httpx.get para ver QUÉ enviaría."""
    enviado = {}

    def get_falso(url, **kwargs):
        enviado.update(url=url, **kwargs)
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", url))

    monkeypatch.setattr(clima.httpx, "get", get_falso)
    assert LLAMAR_HTTP_REAL({"latitude": 31.74}) == {"ok": True}
    assert enviado["url"] == "https://api.open-meteo.com/v1/forecast"
    assert enviado["timeout"] == 5
    # Sin correos ni datos personales en el encabezado
    assert enviado["headers"] == {"User-Agent": "LiebreUrbana-proyecto-escolar"}
    assert "@" not in clima.USER_AGENT


# --- Caché de 1 hora (CA3) ---------------------------------------------------------------------------
def test_la_segunda_llamada_sale_de_la_cache_sin_red(client, open_meteo, reloj):
    primera = client.get(URL).json()
    reloj["ahora"] += timedelta(minutes=59)
    open_meteo.error = httpx.ConnectError("sin red")  # si volviera a consultar, fallaría
    segunda = client.get(URL).json()
    assert primera == segunda and segunda["disponible"] is True
    assert len(open_meteo.llamadas) == 1


def test_la_cache_vence_despues_de_1_hora(client, open_meteo, reloj):
    client.get(URL)
    reloj["ahora"] += timedelta(hours=1, seconds=1)
    open_meteo.respuesta = pronostico(h25_23=70)
    cuerpo = client.get(URL).json()
    assert len(open_meteo.llamadas) == 2
    assert cuerpo["probabilidad_max_pct"] == 70
    assert cuerpo["consultado_en"] == "2026-11-25T22:30:01Z"


# --- Si el servicio falla, la plataforma sigue (CA4) --------------------------------------------------
def peticion_fallida():
    peticion = httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
    return httpx.HTTPStatusError("500", request=peticion, response=httpx.Response(500, request=peticion))


@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectTimeout("tardó"),
        httpx.ReadTimeout("tardó"),
        httpx.ConnectError("sin red"),
        ValueError("no es JSON"),
    ],
)
def test_si_open_meteo_falla_responde_200_no_disponible(client, open_meteo, reloj, error):
    open_meteo.error = error
    r = client.get(URL)
    assert r.status_code == 200
    assert r.json() == {
        "disponible": False,
        "hay_aviso": False,
        "probabilidad_max_pct": None,
        "horas": 12,
        "umbral_pct": 30,
        "consultado_en": None,
    }


def test_error_http_de_open_meteo_responde_200_no_disponible(client, open_meteo, reloj):
    open_meteo.error = peticion_fallida()
    r = client.get(URL)
    assert r.status_code == 200 and r.json()["disponible"] is False


@pytest.mark.parametrize(
    "respuesta",
    [
        [],
        "texto",
        {},
        {"hourly": None},
        {"hourly": {}},
        {"hourly": {"time": ["2026-11-25T15:00"], "precipitation_probability": []}},  # listas de distinto largo
        {"hourly": {"time": ["no es una hora"], "precipitation_probability": [50]}},
        {"hourly": {"time": ["2026-11-25T15:00"], "precipitation_probability": ["mucha"]}},
        {"hourly": {"time": ["2026-11-25T15:00"], "precipitation_probability": [250]}},
        {"hourly": {"time": ["2026-11-25T15:00"], "precipitation_probability": [True]}},
        {"hourly": {"time": ["2026-11-24T15:00"], "precipitation_probability": [80]}},  # nada dentro de la ventana
    ],
)
def test_json_invalido_responde_200_no_disponible(client, open_meteo, reloj, respuesta):
    open_meteo.respuesta = respuesta
    r = client.get(URL)
    assert r.status_code == 200
    assert r.json()["disponible"] is False and r.json()["hay_aviso"] is False


def test_un_fallo_solo_se_recuerda_unos_segundos(client, open_meteo, reloj):
    open_meteo.error = httpx.ConnectError("sin red")
    assert client.get(URL).json()["disponible"] is False
    reloj["ahora"] += timedelta(seconds=10)
    client.get(URL)
    assert len(open_meteo.llamadas) == 1  # dentro de los 30 s no se insiste

    # El servicio se recupera: pasados los 30 s se vuelve a consultar, sin esperar una hora
    reloj["ahora"] += timedelta(seconds=21)
    open_meteo.error = None
    open_meteo.respuesta = pronostico(h25_20=55)
    cuerpo = client.get(URL).json()
    assert len(open_meteo.llamadas) == 2
    assert cuerpo["disponible"] is True and cuerpo["hay_aviso"] is True


# --- Público y sin datos personales ----------------------------------------------------------------
def test_es_publico_y_la_respuesta_no_trae_datos_personales(client, open_meteo, reloj):
    r = client.get(URL)  # sin token
    assert r.status_code == 200
    assert set(r.json()) == {
        "disponible",
        "hay_aviso",
        "probabilidad_max_pct",
        "horas",
        "umbral_pct",
        "consultado_en",
    }
