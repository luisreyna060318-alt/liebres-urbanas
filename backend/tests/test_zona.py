"""¿Cómo está mi zona? (HU-04.3): radio de 1 km, orden, intransitables primero, activos, privacidad y tope."""

from datetime import timedelta

import pytest

from app.core.geo import METROS_POR_GRADO_LAT
from app.core.reglas import RADIO_ZONA_KM
from app.core.tiempo import ahora_utc
from app.models import Reporte
from app.services import zona as zona_service
from tests.conftest import LAT_BASE, LLAVES_PROHIBIDAS, LON_BASE, llaves_de

RUTA = "/api/zona"


@pytest.fixture()
def poner(db, catalogo, ciudadano):
    """Fábrica: crea un reporte a `metros` al norte del punto base. Devuelve el reporte guardado."""
    contador = {"n": 0}

    def _poner(categoria: str, metros: float, estado: str | None = None, **campos) -> Reporte:
        contador["n"] += 1
        comunes = dict(
            autor_id=ciudadano.id, colonia_id=catalogo["colonia"].id, calle="Calle Ficticia",
            lat=LAT_BASE + metros / METROS_POR_GRADO_LAT, lon=LON_BASE,
        )
        if categoria == "bache":
            reporte = Reporte(
                folio=f"BCH-2026-{contador['n']:06d}", categoria="bache", tipo_dano_id=catalogo["tipos"]["bache"].id,
                severidad="media", tamano="mediano", profundidad="media", carril="derecho",
                estado=estado or "recibido", **comunes, **campos,
            )
        else:
            datos = {"nivel_agua": "cubre_carril", "vigente_hasta": ahora_utc() + timedelta(hours=6), **campos}
            reporte = Reporte(
                folio=f"ENC-2026-{contador['n']:06d}", categoria="encharcamiento", estado=estado or "activo",
                **comunes, **datos,
            )
        db.add(reporte)
        db.commit()
        return reporte

    return _poner


def pedir_zona(client, lat: float = LAT_BASE, lon: float = LON_BASE):
    return client.get(RUTA, params={"lat": lat, "lon": lon})


def ids(respuesta) -> list[int]:
    return [r["id"] for r in respuesta.json()["items"]]


# --- Radio de 1 km y distancia ----------------------------------------------------------------------
def test_es_publico_y_responde_la_forma_del_contrato(client, poner):
    poner("bache", 100)
    r = pedir_zona(client)  # sin token
    assert r.status_code == 200
    datos = r.json()
    assert datos["centro"] == {"lat": LAT_BASE, "lon": LON_BASE}
    assert datos["radio_m"] == RADIO_ZONA_KM * 1000
    assert datos["total"] == 1 and len(datos["items"]) == 1


def test_a_900_m_entra_y_a_1200_m_no(client, poner):
    cerca = poner("bache", 900)
    poner("bache", 1200)
    poner("encharcamiento", 1200)
    r = pedir_zona(client)
    assert ids(r) == [cerca.id]
    assert r.json()["total"] == 1


def test_ordena_por_distancia_y_trae_la_distancia_en_metros(client, poner):
    lejos = poner("bache", 700)
    medio = poner("encharcamiento", 400)
    cerca = poner("bache", 50)
    r = pedir_zona(client)
    assert ids(r) == [cerca.id, medio.id, lejos.id]
    distancias = [i["distancia_m"] for i in r.json()["items"]]
    assert distancias == sorted(distancias)
    assert 48 <= distancias[0] <= 52 and 398 <= distancias[1] <= 402 and 698 <= distancias[2] <= 702


def test_intransitable_va_primero_aunque_este_mas_lejos(client, poner):
    bache_cerca = poner("bache", 30)
    media_llanta = poner("encharcamiento", 60, nivel_agua="media_llanta")
    intransitable_lejos = poner("encharcamiento", 800, nivel_agua="intransitable", hay_riesgo=False)
    intransitable_cerca = poner("encharcamiento", 500, nivel_agua="intransitable", hay_riesgo=True)
    r = pedir_zona(client)
    # Primero los intransitables (el más cercano antes), luego el resto por distancia
    assert ids(r) == [intransitable_cerca.id, intransitable_lejos.id, bache_cerca.id, media_llanta.id]
    assert r.json()["items"][0]["nivel_agua"] == "intransitable"


# --- Solo reportes activos --------------------------------------------------------------------------
def test_baches_abiertos_entran_y_reparados_o_rechazados_no(client, db, poner):
    abiertos = [poner("bache", 100 + i, estado=e).id for i, e in enumerate(["recibido", "validado", "en_reparacion"])]
    poner("bache", 150, estado="rechazado")
    reparado = poner("bache", 160, estado="reparado", fecha_reparacion=ahora_utc().date())
    assert reparado.estado == "reparado"
    assert sorted(ids(pedir_zona(client))) == sorted(abiertos)


def test_encharcamientos_historicos_y_rechazados_no_aparecen(client, poner):
    activo = poner("encharcamiento", 100)
    poner("encharcamiento", 110, estado="historico")
    poner("encharcamiento", 120, estado="rechazado")
    assert ids(pedir_zona(client)) == [activo.id]


def test_encharcamiento_vencido_no_aparece_y_pasa_a_historico(client, db, poner):
    vigente = poner("encharcamiento", 100)
    vencido = poner("encharcamiento", 50, vigente_hasta=ahora_utc() - timedelta(minutes=1))
    assert ids(pedir_zona(client)) == [vigente.id]
    db.refresh(vencido)
    assert vencido.estado == "historico"  # se llamó a expirar_vencidos antes de leer


# --- Validación -------------------------------------------------------------------------------------
def test_fuera_del_municipio_responde_422(client):
    r = pedir_zona(client, 32.5, -106.4)  # Estados Unidos
    assert r.status_code == 422
    assert r.json()["codigo"] == "FUERA_DEL_MUNICIPIO"


@pytest.mark.parametrize("params", [{}, {"lat": 31.7}, {"lat": 95, "lon": -106.4}, {"lat": 31.7, "lon": -200},
                                    {"lat": "abc", "lon": -106.4}])
def test_coordenadas_invalidas_o_ausentes_responden_422_validacion(client, params):
    r = client.get(RUTA, params=params)
    assert r.status_code == 422
    assert r.json()["codigo"] == "VALIDACION"


# --- Privacidad y tope ------------------------------------------------------------------------------
def test_la_respuesta_no_trae_autor(client, poner):
    poner("bache", 100)
    poner("encharcamiento", 200, nivel_agua="intransitable", hay_riesgo=True)
    datos = pedir_zona(client).json()
    assert not (llaves_de(datos) & LLAVES_PROHIBIDAS)
    assert "ciudadano@ejemplo.test" not in str(datos)


def test_el_tope_recorta_pero_conserva_intransitables_y_el_total(client, poner, monkeypatch):
    monkeypatch.setattr(zona_service, "MAX_RESULTADOS_ZONA", 3)
    for metros in (10, 20, 30, 40):
        poner("bache", metros)
    intransitable = poner("encharcamiento", 900, nivel_agua="intransitable", hay_riesgo=True)
    datos = pedir_zona(client).json()
    assert datos["total"] == 5
    assert len(datos["items"]) == 3
    assert datos["items"][0]["id"] == intransitable.id  # el más lejano pero intransitable no se pierde


def test_sin_reportes_devuelve_lista_vacia(client):
    datos = pedir_zona(client).json()
    assert datos["total"] == 0 and datos["items"] == []
