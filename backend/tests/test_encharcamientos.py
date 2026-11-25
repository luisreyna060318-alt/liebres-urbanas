"""Encharcamientos: alta (HU-03.1), vigencia automática (HU-03.2) y confirmar o desmentir (HU-03.3).

Para "adelantar el reloj" se inyecta `ahora` en los servicios: ninguna prueba espera 6 horas ni duerme.
"""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.geo import METROS_POR_GRADO_LAT
from app.core.reglas import MAX_REPORTES_POR_HORA
from app.core.tiempo import ahora_utc, como_utc
from app.models import Confirmacion, HistorialEstado, Reporte
from app.schemas.reportes import EncharcamientoEntrada
from app.services import confirmaciones as confirmaciones_service
from app.services import encharcamientos as encharcamientos_service
from app.services.encharcamientos import COMENTARIO_DESMENTIDO, COMENTARIO_VENCIDO, expirar_vencidos
from tests.conftest import LAT_BASE, LLAVES_PROHIBIDAS, LON_BASE, datos_bache, encabezado_de, llaves_de, punto

RUTA = "/api/reportes/encharcamientos"
SEIS_HORAS = timedelta(hours=6)


def datos_encharcamiento(colonia_id: int, n: int = 0, /, **cambios) -> dict:
    lat, lon = punto(n)
    datos = {"lat": lat, "lon": lon, "calle": "Av. de las Torres", "colonia_id": colonia_id, "descripcion": "",
             "nivel_agua": "cubre_carril", "hay_riesgo": None, "forzar": False}
    datos.update(cambios)
    return datos


@pytest.fixture()
def alta(client, ciudadano, catalogo):
    """alta(n, usuario=..., **cambios) -> respuesta HTTP del alta de un encharcamiento."""

    def _alta(n: int = 0, usuario=None, **cambios):
        return client.post(RUTA, json=datos_encharcamiento(catalogo["colonia"].id, n, **cambios),
                           headers=encabezado_de(usuario or ciudadano))

    return _alta


@pytest.fixture()
def vecinos(crear_usuario):
    return [crear_usuario(f"vecino{i}@ejemplo.test") for i in range(4)]


@pytest.fixture()
def encharcamiento(db, ciudadano, catalogo):
    """Un encharcamiento activo creado con el servicio "hace un rato" (el reloj de la prueba arranca en t0)."""
    t0 = ahora_utc() - timedelta(minutes=1)
    creado = encharcamientos_service.crear_encharcamiento(
        db, ciudadano, EncharcamientoEntrada(**datos_encharcamiento(catalogo["colonia"].id)), ahora=t0
    )
    return db.get(Reporte, creado.id), t0


def responder(client, usuario, reporte_id, tipo):
    return client.post(f"/api/reportes/{reporte_id}/confirmaciones", json={"tipo": tipo},
                       headers=encabezado_de(usuario))


# --- HU-03.1: alta ----------------------------------------------------------------------------------
def test_ca1_crea_activo_con_folio_enc_y_vigencia_de_6_horas(alta, db):
    antes = ahora_utc()
    r = alta()
    assert r.status_code == 201
    datos = r.json()
    assert datos["folio"].startswith("ENC-") and datos["categoria"] == "encharcamiento"
    assert datos["estado"] == "activo" and datos["sin_validar"] is False  # se publica de inmediato (RN-06)
    assert datos["tipo_dano"] is None and datos["severidad"] is None and datos["tamano"] is None
    assert datos["puede_editar"] is False
    reporte = db.get(Reporte, datos["id"])
    vigencia = como_utc(reporte.vigente_hasta) - como_utc(reporte.creado_en)
    assert vigencia == SEIS_HORAS and como_utc(reporte.creado_en) >= antes - timedelta(seconds=1)
    fila = db.scalar(select(HistorialEstado).where(HistorialEstado.reporte_id == reporte.id))
    assert fila.estado_anterior is None and fila.estado_nuevo == "activo"
    assert not (llaves_de(datos) & LLAVES_PROHIBIDAS)


@pytest.mark.parametrize("nivel", ["a_un_lado", "cubre_carril", "media_llanta"])
def test_ca2_niveles_de_agua(alta, nivel):
    r = alta(nivel_agua=nivel)
    assert r.status_code == 201 and r.json()["nivel_agua"] == nivel


def test_ca3_intransitable_exige_hay_riesgo(alta):
    r = alta(nivel_agua="intransitable")
    assert r.status_code == 422 and set(r.json()["campos"]) == {"hay_riesgo"}
    ok = alta(nivel_agua="intransitable", hay_riesgo=True)
    assert ok.status_code == 201 and ok.json()["hay_riesgo"] is True


def test_nivel_no_permitido_o_faltante(client, ciudadano, catalogo, alta):
    assert "nivel_agua" in alta(nivel_agua="hasta_el_techo").json()["campos"]
    datos = datos_encharcamiento(catalogo["colonia"].id)
    datos.pop("nivel_agua")
    assert client.post(RUTA, json=datos, headers=encabezado_de(ciudadano)).json()["campos"]["nivel_agua"] == \
        "Este campo es obligatorio"


def test_mismas_validaciones_de_municipio_colonia_y_descripcion(alta, catalogo):
    assert alta(lat=28.63, lon=-106.08).json()["codigo"] == "FUERA_DEL_MUNICIPIO"
    assert "colonia_id" in alta(colonia_id=catalogo["inactiva"].id).json()["campos"]
    assert "descripcion" in alta(descripcion="x" * 501).json()["campos"]


def test_el_limite_por_hora_cuenta_baches_y_encharcamientos(client, ciudadano, catalogo, alta):
    for n in range(MAX_REPORTES_POR_HORA - 1):
        assert client.post("/api/reportes/baches", json=datos_bache(catalogo["colonia"].id, n),
                           headers=encabezado_de(ciudadano)).status_code == 201
    assert alta(50).status_code == 201  # el décimo
    r = alta(60)
    assert r.status_code == 429 and r.json()["codigo"] == "LIMITE_HORARIO"


@pytest.mark.parametrize("rol", ["moderador", "coordinador"])
def test_solo_el_ciudadano_reporta(alta, crear_usuario, rol):
    assert alta(usuario=crear_usuario(f"{rol}@ejemplo.test", rol=rol)).json()["codigo"] == "SIN_PERMISO"


def test_sin_token_responde_401(client, catalogo):
    assert client.post(RUTA, json=datos_encharcamiento(catalogo["colonia"].id)).status_code == 401


# --- HU-03.1 CA4: duplicados a 50 m ------------------------------------------------------------------
def test_ca4_uno_activo_a_40_m_es_posible_duplicado(alta, vecinos):
    existente = alta().json()
    r = alta(usuario=vecinos[0], lat=LAT_BASE + 40 / METROS_POR_GRADO_LAT, lon=LON_BASE)
    assert r.status_code == 409 and r.json()["codigo"] == "POSIBLE_DUPLICADO"
    assert [d["id"] for d in r.json()["duplicados"]] == [existente["id"]]
    assert 38 <= r.json()["duplicados"][0]["distancia_m"] <= 42


def test_a_60_m_no_es_duplicado_y_forzar_crea_uno_nuevo(alta, vecinos):
    alta()
    assert alta(usuario=vecinos[0], lat=LAT_BASE + 60 / METROS_POR_GRADO_LAT, lon=LON_BASE).status_code == 201
    assert alta(usuario=vecinos[1], lat=LAT_BASE + 10 / METROS_POR_GRADO_LAT, lon=LON_BASE,
                forzar=True).status_code == 201


def test_un_bache_cercano_no_es_duplicado_de_un_encharcamiento(client, ciudadano, catalogo, alta, vecinos):
    client.post("/api/reportes/baches", json=datos_bache(catalogo["colonia"].id), headers=encabezado_de(ciudadano))
    assert alta(usuario=vecinos[0]).status_code == 201


def test_uno_vencido_no_cuenta_como_duplicado_y_queda_historico(db, alta, vecinos):
    viejo = db.get(Reporte, alta().json()["id"])
    viejo.vigente_hasta = ahora_utc() - timedelta(minutes=1)  # ya venció, pero nadie lo ha pasado a histórico
    db.commit()
    assert alta(usuario=vecinos[0]).status_code == 201
    db.refresh(viejo)
    assert viejo.estado == "historico"


# --- HU-03.2: vigencia automática ----------------------------------------------------------------
def test_vigencia_de_6_horas_y_paso_a_historico(db, encharcamiento):
    reporte, t0 = encharcamiento
    assert expirar_vencidos(db, ahora=t0 + SEIS_HORAS - timedelta(minutes=1)) == 0
    assert reporte.estado == "activo"
    assert expirar_vencidos(db, ahora=t0 + SEIS_HORAS) == 1
    db.refresh(reporte)
    assert reporte.estado == "historico"
    ultima = db.scalars(select(HistorialEstado).where(HistorialEstado.reporte_id == reporte.id)
                        .order_by(HistorialEstado.id.desc())).first()
    assert ultima.estado_anterior == "activo" and ultima.estado_nuevo == "historico"
    assert ultima.actor_id is None and ultima.comentario == COMENTARIO_VENCIDO  # "sistema"
    assert expirar_vencidos(db, ahora=t0 + SEIS_HORAS * 2) == 0  # ya no se vuelve a tocar


def test_ca2_sigue_ahi_suma_6_horas_desde_ese_momento(db, encharcamiento, vecinos):
    reporte, t0 = encharcamiento
    publico = confirmaciones_service.confirmar(db, vecinos[0], reporte.id, "sigue", ahora=t0 + timedelta(hours=5))
    assert publico.confirmaciones == 1
    assert como_utc(publico.vigente_hasta) == t0 + timedelta(hours=11)
    assert expirar_vencidos(db, ahora=t0 + timedelta(hours=7)) == 0  # sin la confirmación ya habría vencido
    assert expirar_vencidos(db, ahora=t0 + timedelta(hours=11)) == 1


def test_sigue_ahi_por_http(client, encharcamiento, vecinos):
    reporte, _ = encharcamiento
    r = responder(client, vecinos[0], reporte.id, "sigue")
    assert r.status_code == 201
    vence = como_utc(reporte.vigente_hasta)
    assert r.json()["confirmaciones"] == 1
    assert ahora_utc() + SEIS_HORAS - timedelta(seconds=30) <= vence <= ahora_utc() + SEIS_HORAS
    assert not (llaves_de(r.json()) & LLAVES_PROHIBIDAS)


def test_ca3_los_historicos_no_se_borran(db, encharcamiento):
    reporte, t0 = encharcamiento
    expirar_vencidos(db, ahora=t0 + SEIS_HORAS)
    assert db.scalar(select(func.count()).select_from(Reporte).where(Reporte.estado == "historico")) == 1


def test_un_vencido_no_admite_respuestas(client, db, encharcamiento, vecinos):
    reporte, _ = encharcamiento
    reporte.vigente_hasta = ahora_utc() - timedelta(seconds=1)
    db.commit()
    r = responder(client, vecinos[0], reporte.id, "sigue")
    assert r.status_code == 409 and r.json()["codigo"] == "TRANSICION_INVALIDA"
    db.refresh(reporte)
    assert reporte.estado == "historico"


# --- HU-03.3: confirmar o desmentir ----------------------------------------------------------------
def test_ca3_tres_desmentidos_de_personas_distintas_lo_cierran(client, db, encharcamiento, vecinos):
    reporte, _ = encharcamiento
    for vecino in vecinos[:2]:
        assert responder(client, vecino, reporte.id, "ya_no_hay").json()["estado"] == "activo"
    r = responder(client, vecinos[2], reporte.id, "ya_no_hay")
    assert r.status_code == 201 and r.json()["estado"] == "historico"
    assert r.json()["confirmaciones"] == 0  # desmentir no suma confirmaciones
    ultima = db.scalars(select(HistorialEstado).where(HistorialEstado.reporte_id == reporte.id)
                        .order_by(HistorialEstado.id.desc())).first()
    assert ultima.actor_id is None and ultima.comentario == COMENTARIO_DESMENTIDO
    # Cada desmentido quedó con su fecha y hora
    fechas = list(db.scalars(select(Confirmacion.creado_en).where(Confirmacion.tipo == "ya_no_hay")))
    assert len(fechas) == 3 and all(f is not None for f in fechas)


def test_el_segundo_desmentido_de_la_misma_persona_no_cuenta(client, encharcamiento, vecinos):
    reporte, _ = encharcamiento
    responder(client, vecinos[0], reporte.id, "ya_no_hay")
    r = responder(client, vecinos[0], reporte.id, "ya_no_hay")
    assert r.status_code == 409 and r.json()["codigo"] == "YA_CONFIRMADO"
    responder(client, vecinos[1], reporte.id, "ya_no_hay")
    assert responder(client, vecinos[1], reporte.id, "ya_no_hay").status_code == 409
    assert reporte.estado == "activo"  # solo 2 personas distintas


def test_una_respuesta_por_persona_aunque_cambie_de_opinion(client, encharcamiento, vecinos):
    reporte, _ = encharcamiento
    responder(client, vecinos[0], reporte.id, "sigue")
    assert responder(client, vecinos[0], reporte.id, "ya_no_hay").json()["codigo"] == "YA_CONFIRMADO"


def test_ca4_el_autor_no_confirma_ni_desmiente_el_suyo(client, ciudadano, encharcamiento):
    reporte, _ = encharcamiento
    for tipo in ("sigue", "ya_no_hay"):
        r = responder(client, ciudadano, reporte.id, tipo)
        assert r.status_code == 403 and r.json()["codigo"] == "ES_TU_REPORTE"


def test_confirma_no_aplica_a_encharcamientos(client, encharcamiento, vecinos):
    reporte, _ = encharcamiento
    r = responder(client, vecinos[0], reporte.id, "confirma")
    assert r.status_code == 422 and "tipo" in r.json()["campos"]


def test_un_historico_no_admite_respuestas(client, db, encharcamiento, vecinos):
    reporte, t0 = encharcamiento
    expirar_vencidos(db, ahora=t0 + SEIS_HORAS)
    assert responder(client, vecinos[0], reporte.id, "sigue").json()["codigo"] == "TRANSICION_INVALIDA"


# --- Cercanos y mis reportes llaman a expirar_vencidos ------------------------------------------------
def test_cercanos_de_encharcamientos_a_50_m(client, db, alta, vecinos, ciudadano):
    cerca = alta().json()
    lejos = alta(usuario=vecinos[0], lat=LAT_BASE + 45 / METROS_POR_GRADO_LAT, lon=LON_BASE).json()
    fuera = alta(usuario=vecinos[1], lat=LAT_BASE + 120 / METROS_POR_GRADO_LAT, lon=LON_BASE).json()
    assert "id" in cerca and "id" in fuera and lejos["codigo"] == "POSIBLE_DUPLICADO"
    lejos = alta(usuario=vecinos[0], lat=LAT_BASE + 45 / METROS_POR_GRADO_LAT, lon=LON_BASE, forzar=True).json()
    r = client.get("/api/reportes/cercanos", params={"categoria": "encharcamiento", "lat": LAT_BASE, "lon": LON_BASE},
                   headers=encabezado_de(vecinos[2]))
    assert r.status_code == 200
    assert [c["id"] for c in r.json()] == [cerca["id"], lejos["id"]]
    assert r.json()[0]["distancia_m"] == 0


def test_cercanos_pasa_a_historico_los_vencidos(client, db, alta, vecinos):
    reporte = db.get(Reporte, alta().json()["id"])
    reporte.vigente_hasta = ahora_utc() - timedelta(minutes=5)
    db.commit()
    r = client.get("/api/reportes/cercanos", params={"categoria": "encharcamiento", "lat": LAT_BASE, "lon": LON_BASE},
                   headers=encabezado_de(vecinos[0]))
    assert r.json() == []
    db.refresh(reporte)
    assert reporte.estado == "historico"


def test_mis_reportes_muestra_los_vencidos_como_historico(client, db, ciudadano, alta):
    reporte = db.get(Reporte, alta().json()["id"])
    reporte.vigente_hasta = ahora_utc() - timedelta(minutes=5)
    db.commit()
    item = client.get("/api/mis-reportes", headers=encabezado_de(ciudadano)).json()["items"][0]
    assert item["estado"] == "historico" and item["puede_editar"] is False


def test_un_encharcamiento_no_se_edita_ni_se_borra(client, ciudadano, catalogo, encharcamiento):
    reporte, _ = encharcamiento
    datos = datos_bache(catalogo["colonia"].id)
    datos.pop("forzar")
    assert client.put(f"/api/reportes/{reporte.id}", json=datos, headers=encabezado_de(ciudadano)).json()["codigo"] \
        == "REPORTE_NO_EDITABLE"
    assert client.delete(f"/api/reportes/{reporte.id}", headers=encabezado_de(ciudadano)).status_code == 409
