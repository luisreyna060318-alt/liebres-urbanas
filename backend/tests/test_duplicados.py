"""Duplicados y confirmaciones de baches (HU-02.3)."""

import pytest
from sqlalchemy import false, func, select

from app.core.geo import METROS_POR_GRADO_LAT
from app.models import Confirmacion, Reporte
from app.services import confirmaciones as confirmaciones_service
from tests.conftest import LAT_BASE, LLAVES_PROHIBIDAS, LON_BASE, datos_bache, encabezado_de, llaves_de

RUTA_ALTA = "/api/reportes/baches"


def a_metros_al_norte(metros: float) -> tuple[float, float]:
    """Punto a `metros` al norte del punto base (1 grado de latitud ≈ 111 320 m)."""
    return LAT_BASE + metros / METROS_POR_GRADO_LAT, LON_BASE


@pytest.fixture()
def vecina(crear_usuario):
    return crear_usuario("vecina@ejemplo.test")


@pytest.fixture()
def bache_existente(client, ciudadano, catalogo):
    """Un bache del ciudadano de prueba en el punto base."""
    r = client.post(RUTA_ALTA, json=datos_bache(catalogo["colonia"].id), headers=encabezado_de(ciudadano))
    assert r.status_code == 201
    return r.json()


def alta_en(client, usuario, catalogo, lat, lon, **cambios):
    return client.post(
        RUTA_ALTA, json=datos_bache(catalogo["colonia"].id, 0, lat=lat, lon=lon, **cambios),
        headers=encabezado_de(usuario),
    )


def confirmar(client, usuario, reporte_id, tipo="confirma"):
    ruta = f"/api/reportes/{reporte_id}/confirmaciones"
    return client.post(ruta, json={"tipo": tipo}, headers=encabezado_de(usuario))


# --- Detección de duplicados ----------------------------------------------------------------------
def test_ca1_bache_a_20_m_responde_posible_duplicado(client, vecina, catalogo, bache_existente):
    r = alta_en(client, vecina, catalogo, *a_metros_al_norte(20))
    assert r.status_code == 409
    datos = r.json()
    assert datos["codigo"] == "POSIBLE_DUPLICADO"
    assert [d["id"] for d in datos["duplicados"]] == [bache_existente["id"]]
    assert 18 <= datos["duplicados"][0]["distancia_m"] <= 22
    assert not (llaves_de(datos) & LLAVES_PROHIBIDAS)


def test_bache_a_40_m_no_es_duplicado(client, vecina, catalogo, bache_existente):
    assert alta_en(client, vecina, catalogo, *a_metros_al_norte(40)).status_code == 201


def test_ca4_con_forzar_se_crea_uno_nuevo(client, vecina, catalogo, bache_existente, db):
    r = alta_en(client, vecina, catalogo, *a_metros_al_norte(10), forzar=True)
    assert r.status_code == 201
    assert r.json()["folio"] != bache_existente["folio"]
    assert db.scalar(select(func.count()).select_from(Reporte)) == 2


@pytest.mark.parametrize("estado", ["reparado", "rechazado"])
def test_baches_cerrados_no_cuentan_como_duplicado(client, vecina, catalogo, bache_existente, db, estado):
    reporte = db.get(Reporte, bache_existente["id"])
    reporte.estado = estado
    if estado == "reparado":
        reporte.fecha_reparacion = reporte.creado_en.date()
    db.commit()
    assert alta_en(client, vecina, catalogo, *a_metros_al_norte(5)).status_code == 201


@pytest.mark.parametrize("estado", ["validado", "en_reparacion"])
def test_baches_abiertos_en_otros_estados_si_cuentan(client, vecina, catalogo, bache_existente, db, estado):
    db.get(Reporte, bache_existente["id"]).estado = estado
    db.commit()
    assert alta_en(client, vecina, catalogo, *a_metros_al_norte(5)).status_code == 409


# --- GET /api/reportes/cercanos ----------------------------------------------------------------
def test_cercanos_ordenados_por_distancia(client, vecina, catalogo, bache_existente, ciudadano):
    lat, lon = a_metros_al_norte(25)
    segundo = alta_en(client, ciudadano, catalogo, lat, lon, forzar=True).json()
    consulta_lat, _ = a_metros_al_norte(20)  # a 20 m del primero y a 5 m del segundo
    r = client.get(
        "/api/reportes/cercanos", params={"categoria": "bache", "lat": consulta_lat, "lon": LON_BASE},
        headers=encabezado_de(vecina),
    )
    assert r.status_code == 200
    assert [c["id"] for c in r.json()] == [segundo["id"], bache_existente["id"]]
    assert r.json()[0]["distancia_m"] <= r.json()[1]["distancia_m"]


def test_cercanos_sin_resultados_es_lista_vacia(client, vecina, catalogo):
    r = client.get("/api/reportes/cercanos", params={"categoria": "bache", "lat": 31.7, "lon": -106.4},
                   headers=encabezado_de(vecina))
    assert r.status_code == 200 and r.json() == []


def test_cercanos_valida_parametros(client, vecina):
    r = client.get("/api/reportes/cercanos", params={"categoria": "otro", "lat": 31.7},
                   headers=encabezado_de(vecina))
    assert r.status_code == 422
    assert {"categoria", "lon"} <= set(r.json()["campos"])


def test_cercanos_pide_rol_ciudadano(client, moderador):
    params = {"categoria": "bache", "lat": 31.7, "lon": -106.4}
    assert client.get("/api/reportes/cercanos", params=params).status_code == 401
    assert client.get("/api/reportes/cercanos", params=params, headers=encabezado_de(moderador)).status_code == 403


# --- Confirmaciones --------------------------------------------------------------------------
def test_ca2_confirmar_suma_1_sin_crear_folio(client, vecina, bache_existente, db):
    r = confirmar(client, vecina, bache_existente["id"])
    assert r.status_code == 201
    assert r.json()["confirmaciones"] == 1 and r.json()["folio"] == bache_existente["folio"]
    assert db.scalar(select(func.count()).select_from(Reporte)) == 1
    assert not (llaves_de(r.json()) & LLAVES_PROHIBIDAS)


def test_ca3_una_sola_confirmacion_por_persona(client, vecina, bache_existente, db):
    confirmar(client, vecina, bache_existente["id"])
    r = confirmar(client, vecina, bache_existente["id"])
    assert r.status_code == 409 and r.json()["codigo"] == "YA_CONFIRMADO"
    assert db.get(Reporte, bache_existente["id"]).confirmaciones == 1
    assert db.scalar(select(func.count()).select_from(Confirmacion)) == 1


def test_varias_personas_suman(client, crear_usuario, bache_existente):
    for i in range(3):
        r = confirmar(client, crear_usuario(f"persona{i}@ejemplo.test"), bache_existente["id"])
    assert r.json()["confirmaciones"] == 3


def test_el_autor_no_confirma_su_reporte(client, ciudadano, bache_existente):
    r = confirmar(client, ciudadano, bache_existente["id"])
    assert r.status_code == 403 and r.json()["codigo"] == "ES_TU_REPORTE"


def test_reporte_inexistente_o_rechazado_responde_404(client, vecina, bache_existente, db):
    assert confirmar(client, vecina, 9999).status_code == 404
    db.get(Reporte, bache_existente["id"]).estado = "rechazado"
    db.commit()
    r = confirmar(client, vecina, bache_existente["id"])
    assert r.status_code == 404 and r.json()["codigo"] == "NO_ENCONTRADO"


def test_bache_reparado_no_admite_confirmaciones(client, vecina, bache_existente, db):
    reporte = db.get(Reporte, bache_existente["id"])
    reporte.estado, reporte.fecha_reparacion = "reparado", reporte.creado_en.date()
    db.commit()
    r = confirmar(client, vecina, bache_existente["id"])
    assert r.status_code == 409 and r.json()["codigo"] == "TRANSICION_INVALIDA"


@pytest.mark.parametrize("tipo", ["sigue", "ya_no_hay"])
def test_tipo_de_encharcamiento_en_un_bache_responde_422(client, vecina, bache_existente, tipo):
    r = confirmar(client, vecina, bache_existente["id"], tipo)
    assert r.status_code == 422 and "tipo" in r.json()["campos"]


def test_tipo_desconocido_responde_422(client, vecina, bache_existente):
    assert confirmar(client, vecina, bache_existente["id"], "me_gusta").status_code == 422


@pytest.mark.parametrize("rol", ["moderador", "coordinador"])
def test_otros_roles_no_confirman(client, crear_usuario, bache_existente, rol):
    r = confirmar(client, crear_usuario(f"{rol}@ejemplo.test", rol=rol), bache_existente["id"])
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"


def test_confirmar_sin_token_responde_401(client, bache_existente):
    assert client.post(f"/api/reportes/{bache_existente['id']}/confirmaciones", json={"tipo": "confirma"}).status_code \
        == 401


def test_confirmacion_simultanea_la_detiene_la_base(db, vecina, bache_existente, monkeypatch):
    """Si dos peticiones pasan la revisión a la vez, la restricción única (reporte, usuario) frena la segunda."""
    confirmaciones_service.confirmar(db, vecina, bache_existente["id"], "confirma")
    # Simulamos que la revisión previa "no vio" la primera confirmación
    monkeypatch.setattr(confirmaciones_service, "select", lambda *_: select(Confirmacion).where(false()))
    with pytest.raises(Exception) as error:
        confirmaciones_service.confirmar(db, vecina, bache_existente["id"], "confirma")
    assert getattr(error.value, "codigo", None) == "YA_CONFIRMADO"
    assert db.get(Reporte, bache_existente["id"]).confirmaciones == 1
