"""Ubicación con Nominatim (HU-02.1 CA1, RN-01). La red SIEMPRE se simula: ninguna prueba sale a internet."""

import httpx
import pytest

from app.core.geo import dentro_del_municipio
from app.models import Colonia, Sector
from app.services import geocodificacion
from app.services.geocodificacion import normalizar_nombre

LUGAR_TECNOLOGICO = {
    "lat": "31.7001",
    "lon": "-106.4302",
    "display_name": "Avenida Tecnológico, Partido Escobedo, Ciudad Juárez, Chihuahua, México",
    "address": {"road": "Avenida Tecnológico", "suburb": "PARTIDO ESCOBEDO", "city": "Ciudad Juárez"},
}


class NominatimFalso:
    """Reemplaza a geocodificacion._llamar_http: responde lo que se le indique y anota cada llamada."""

    def __init__(self, respuesta=None, error: Exception | None = None):
        self.respuesta = respuesta
        self.error = error
        self.llamadas: list[tuple[str, dict]] = []

    def __call__(self, ruta, parametros):
        self.llamadas.append((ruta, parametros))
        if self.error:
            raise self.error
        return self.respuesta


@pytest.fixture()
def nominatim(monkeypatch):
    """Instala un Nominatim falso; la prueba ajusta .respuesta o .error."""
    falso = NominatimFalso(respuesta=[])
    monkeypatch.setattr(geocodificacion, "_llamar_http", falso)
    return falso


@pytest.fixture()
def reloj(monkeypatch):
    """Reloj simulado: las pruebas del límite de ritmo no duermen de verdad, solo anotan cuánto esperarían."""
    estado = {"ahora": 1000.0, "esperas": []}

    def dormir(segundos):
        estado["esperas"].append(segundos)
        estado["ahora"] += segundos

    monkeypatch.setattr(geocodificacion, "_reloj", lambda: estado["ahora"])
    monkeypatch.setattr(geocodificacion, "_dormir", dormir)
    return estado


@pytest.fixture()
def partido_escobedo(db):
    sector = Sector(nombre="Centro")
    db.add(sector)
    db.flush()
    colonia = Colonia(nombre="Partido Escobedo", sector_id=sector.id)
    db.add(colonia)
    db.commit()
    return colonia


# --- Búsqueda -------------------------------------------------------------------------------------
def test_buscar_devuelve_resultados_con_colonia_del_catalogo(client, nominatim, partido_escobedo):
    nominatim.respuesta = [LUGAR_TECNOLOGICO]
    r = client.get("/api/geo/buscar", params={"q": "Av. Tecnológico 1340"})
    assert r.status_code == 200
    assert r.json() == {
        "resultados": [
            {
                "etiqueta": LUGAR_TECNOLOGICO["display_name"],
                "lat": 31.7001,
                "lon": -106.4302,
                "calle": "Avenida Tecnológico",
                "colonia_id": partido_escobedo.id,
                "colonia_nombre": "Partido Escobedo",
                "dentro_del_municipio": True,
            }
        ]
    }


def test_buscar_restringe_a_juarez_y_usa_user_agent_generico(client, nominatim):
    client.get("/api/geo/buscar", params={"q": "Av. Tecnológico"})
    ruta, parametros = nominatim.llamadas[0]
    assert ruta == "search"
    assert parametros["countrycodes"] == "mx" and parametros["bounded"] == 1
    assert parametros["format"] == "jsonv2" and parametros["addressdetails"] == 1
    assert parametros["viewbox"] == "-106.9516255,31.7838974,-106.1808825,31.1199567"
    # Sin correos ni datos personales en el encabezado
    assert geocodificacion.USER_AGENT == "LiebreUrbana-proyecto-escolar"
    assert "@" not in geocodificacion.USER_AGENT


def test_buscar_sin_coincidencias_no_es_error(client, nominatim):
    nominatim.respuesta = []
    r = client.get("/api/geo/buscar", params={"q": "Calle que no existe 999"})
    assert r.status_code == 200
    assert r.json() == {"resultados": []}


def test_colonia_sin_coincidencia_queda_en_null(client, nominatim, partido_escobedo):
    nominatim.respuesta = [{**LUGAR_TECNOLOGICO, "address": {"road": "Calle X", "suburb": "Colonia Inventada"}}]
    resultado = client.get("/api/geo/buscar", params={"q": "Calle X"}).json()["resultados"][0]
    assert resultado["colonia_id"] is None and resultado["colonia_nombre"] is None
    assert resultado["calle"] == "Calle X"


@pytest.mark.parametrize("q", ["", "  ", "ab", "  z  "])
def test_busqueda_vacia_o_muy_corta_responde_422(client, nominatim, q):
    r = client.get("/api/geo/buscar", params={"q": q})
    assert r.status_code == 422
    assert r.json()["codigo"] == "VALIDACION" and "q" in r.json()["campos"]
    assert nominatim.llamadas == []  # ni siquiera se consultó a Nominatim


@pytest.mark.parametrize(
    "error", [httpx.ConnectTimeout("tardó"), httpx.ConnectError("sin red"), ValueError("no es JSON")]
)
def test_si_nominatim_falla_responde_503(client, nominatim, error):
    nominatim.error = error
    r = client.get("/api/geo/buscar", params={"q": "Av. Tecnológico"})
    assert r.status_code == 503
    assert r.json()["codigo"] == "SERVICIO_NO_DISPONIBLE"


def test_error_http_de_nominatim_responde_503(client, nominatim):
    peticion = httpx.Request("GET", "https://nominatim.openstreetmap.org/search")
    nominatim.error = httpx.HTTPStatusError("429", request=peticion, response=httpx.Response(429, request=peticion))
    assert client.get("/api/geo/inversa", params={"lat": 31.7, "lon": -106.4}).status_code == 503


def test_la_misma_busqueda_se_responde_de_la_cache(client, nominatim, reloj):
    nominatim.respuesta = [LUGAR_TECNOLOGICO]
    primera = client.get("/api/geo/buscar", params={"q": "Av. Tecnológico"}).json()
    segunda = client.get("/api/geo/buscar", params={"q": "  Av.   Tecnológico "}).json()  # mismos espacios normalizados
    assert primera == segunda
    assert len(nominatim.llamadas) == 1


def test_la_cache_vence(client, nominatim, reloj):
    client.get("/api/geo/buscar", params={"q": "Av. Tecnológico"})
    reloj["ahora"] += geocodificacion.GEO_CACHE_MIN * 60 + 1
    client.get("/api/geo/buscar", params={"q": "Av. Tecnológico"})
    assert len(nominatim.llamadas) == 2


def test_limite_de_una_peticion_por_segundo(client, nominatim, reloj):
    client.get("/api/geo/buscar", params={"q": "Calle Uno"})
    reloj["ahora"] += 0.3  # la siguiente llega 0.3 s después: debe esperar 0.7 s
    client.get("/api/geo/buscar", params={"q": "Calle Dos"})
    assert len(nominatim.llamadas) == 2
    assert reloj["esperas"] == [pytest.approx(0.7)]


def test_sin_espera_si_ya_paso_un_segundo(client, nominatim, reloj):
    client.get("/api/geo/buscar", params={"q": "Calle Uno"})
    reloj["ahora"] += 1.5
    client.get("/api/geo/buscar", params={"q": "Calle Dos"})
    assert reloj["esperas"] == []


# --- Búsqueda inversa ----------------------------------------------------------------------------
def test_inversa_conserva_el_punto_de_la_persona(client, nominatim, partido_escobedo):
    nominatim.respuesta = LUGAR_TECNOLOGICO
    r = client.get("/api/geo/inversa", params={"lat": 31.70015, "lon": -106.43025})
    assert r.status_code == 200
    datos = r.json()
    assert datos["lat"] == 31.70015 and datos["lon"] == -106.43025
    assert datos["colonia_id"] == partido_escobedo.id and datos["calle"] == "Avenida Tecnológico"
    assert nominatim.llamadas[0][0] == "reverse"


def test_inversa_sin_lugar_devuelve_el_punto_sin_calle(client, nominatim):
    nominatim.respuesta = {"error": "Unable to geocode"}
    datos = client.get("/api/geo/inversa", params={"lat": 31.5, "lon": -106.6}).json()
    assert datos["calle"] is None and datos["colonia_id"] is None
    assert datos["dentro_del_municipio"] is True


def test_inversa_fuera_del_municipio(client, nominatim):
    nominatim.respuesta = {"lat": "19.43", "lon": "-99.13", "display_name": "Ciudad de México", "address": {}}
    datos = client.get("/api/geo/inversa", params={"lat": 19.43, "lon": -99.13}).json()
    assert datos["dentro_del_municipio"] is False


def test_inversa_valida_coordenadas(client, nominatim):
    r = client.get("/api/geo/inversa", params={"lat": 200, "lon": -106.4})
    assert r.status_code == 422 and "lat" in r.json()["campos"]


# --- Normalización y municipio ---------------------------------------------------------------------
@pytest.mark.parametrize(
    "texto",
    [
        "Partido Escobedo",
        "PARTIDO ESCOBEDO",
        "  partido   escobedo ",
        "Col. Partido Escobedo",
        "Colonia Partido Escobedo",
    ],
)
def test_normalizar_nombre_de_colonia(texto):
    assert normalizar_nombre(texto) == "partido escobedo"


def test_normalizar_quita_acentos_y_enie(db, nominatim):
    assert normalizar_nombre("Juárez Peñón") == normalizar_nombre("JUAREZ PENON")


def test_colonia_por_neighbourhood_y_sin_acentos(db, partido_escobedo):
    sector = db.get(Sector, partido_escobedo.sector_id)
    otra = Colonia(nombre="Melchor Ocampo", sector_id=sector.id)
    db.add(otra)
    db.commit()
    encontrada = geocodificacion.buscar_colonia(db, {"neighbourhood": "melchor ocampó"})
    assert encontrada.id == otra.id


def test_colonia_desactivada_no_se_asigna(db, partido_escobedo):
    partido_escobedo.activa = False
    db.commit()
    assert geocodificacion.buscar_colonia(db, {"suburb": "Partido Escobedo"}) is None


@pytest.mark.parametrize(
    "lat,lon,esperado",
    [
        (31.7389744, -106.4832065, True),  # centro de Ciudad Juárez
        (31.6900, -106.4200, True),  # suroriente de la ciudad
        (31.3500, -106.5000, True),  # zona rural del municipio (Samalayuca)
        (28.6353, -106.0889, False),  # ciudad de Chihuahua
        (19.4326, -99.1332, False),  # Ciudad de México
        (31.9000, -106.4000, False),  # norte de El Paso, Texas
    ],
)
def test_dentro_del_municipio(lat, lon, esperado):
    assert dentro_del_municipio(lat, lon) is esperado


def test_ninguna_prueba_sale_a_internet(client):
    """Sin simular la red, la llamada falla (la protege el fixture sin_red de conftest.py)."""
    with pytest.raises(AssertionError, match="sin simular la red"):
        geocodificacion._llamar_http("search", {})
