"""Detalle e historial de un reporte (HU-04.4)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.core.tiempo import a_hora_local, ahora_utc, hoy_local
from app.models import Confirmacion, HistorialEstado, Reporte
from app.services.estados import registrar_cambio_estado
from tests.conftest import LLAVES_PROHIBIDAS, encabezado_de, llaves_de


@pytest.fixture()
def bache(db: Session, catalogo, ciudadano, moderador):
    """Bache creado hace 10 días, validado y en reparación, con su historial y dos confirmaciones."""
    creado = ahora_utc() - timedelta(days=10)
    reporte = Reporte(
        folio="BCH-2026-000777", categoria="bache", tipo_dano_id=catalogo["tipos"]["bache"].id,
        autor_id=ciudadano.id, colonia_id=catalogo["colonia"].id, calle="Av. Tecnológico", lat=31.7, lon=-106.43,
        severidad="alta", tamano="grande", profundidad="media", carril="derecho", estado="recibido",
        confirmaciones=2, creado_en=creado,
    )
    db.add(reporte)
    db.flush()
    db.add(HistorialEstado(reporte_id=reporte.id, estado_anterior=None, estado_nuevo="recibido",
                           actor_id=ciudadano.id, creado_en=creado))
    registrar_cambio_estado(db, reporte, "validado", actor=moderador, comentario="Confirmado en sitio")
    registrar_cambio_estado(db, reporte, "en_reparacion", actor=moderador, comentario="Cuadrilla asignada")
    db.add_all([
        Confirmacion(reporte_id=reporte.id, usuario_id=moderador.id, tipo="confirma",
                     creado_en=datetime(2026, 11, 20, 15, 0, tzinfo=UTC)),
        Confirmacion(reporte_id=reporte.id, usuario_id=ciudadano.id, tipo="confirma",
                     creado_en=datetime(2026, 11, 22, 18, 30, tzinfo=UTC)),
    ])
    db.commit()
    return reporte


def detalle(client, reporte_id, usuario=None):
    return client.get(f"/api/reportes/{reporte_id}", headers=encabezado_de(usuario) if usuario else {})


def test_detalle_completo_de_un_bache(client, bache):
    r = detalle(client, bache.id)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["folio"] == "BCH-2026-000777" and d["categoria"] == "bache"
    assert d["tipo_dano"]["nombre"] == "Bache" and d["calle"] == "Av. Tecnológico"
    assert d["colonia"]["nombre"] == "Partido Escobedo" and d["lat"] == 31.7
    assert (d["tamano"], d["profundidad"], d["carril"], d["severidad"]) == ("grande", "media", "derecho", "alta")
    assert d["confirmaciones"] == 2 and d["estado"] == "en_reparacion"
    assert d["longevidad_dias"] == 10
    assert d["creado_en"].startswith(bache.creado_en.strftime("%Y-%m-%d"))
    assert d["ultima_confirmacion"] == "2026-11-22T18:30:00Z"


def test_historial_del_mas_reciente_al_mas_antiguo_y_sin_actor(client, bache, ciudadano, moderador):
    r = detalle(client, bache.id)
    historial = r.json()["historial"]
    assert [h["estado_nuevo"] for h in historial] == ["en_reparacion", "validado", "recibido"]
    assert historial[0] == {
        "estado_anterior": "validado", "estado_nuevo": "en_reparacion", "comentario": "Cuadrilla asignada",
        "creado_en": historial[0]["creado_en"],
    }
    assert r.json()["ultima_actividad"] == historial[0]["creado_en"]
    assert not (llaves_de(r.json()) & LLAVES_PROHIBIDAS)
    for persona in (ciudadano, moderador):
        assert persona.correo not in r.text and persona.nombre not in r.text


def test_sin_confirmaciones_ultima_confirmacion_es_null(client, db, catalogo, ciudadano):
    reporte = Reporte(folio="BCH-2026-000001", categoria="bache", tipo_dano_id=catalogo["tipos"]["bache"].id,
                      autor_id=ciudadano.id, colonia_id=catalogo["colonia"].id, calle="Calle", lat=31.7, lon=-106.4,
                      severidad="baja", tamano="chico", profundidad="baja", carril="orilla", estado="recibido")
    db.add(reporte)
    db.commit()
    d = detalle(client, reporte.id).json()
    assert d["ultima_confirmacion"] is None and d["historial"] == []
    assert d["ultima_actividad"] == d["creado_en"]  # sin historial, la última actividad es el alta


def test_longevidad_de_un_reparado_llega_hasta_la_reparacion(client, db, bache, moderador):
    reparacion = hoy_local() - timedelta(days=3)
    registrar_cambio_estado(db, bache, "reparado", actor=moderador, fecha_reparacion=reparacion)
    db.commit()
    d = detalle(client, bache.id).json()
    assert d["estado"] == "reparado" and d["fecha_reparacion"] == reparacion.isoformat()
    # creado hace 10 días y reparado hace 3: la longevidad se detiene en la fecha de reparación (7 días)
    assert d["longevidad_dias"] == (reparacion - a_hora_local(bache.creado_en).date()).days == 7


def test_encharcamiento_vencido_se_ve_historico(client, db, catalogo, ciudadano):
    charco = Reporte(folio="ENC-2026-000001", categoria="encharcamiento", autor_id=ciudadano.id,
                     colonia_id=catalogo["colonia"].id, calle="Calle", lat=31.7, lon=-106.4, nivel_agua="cubre_carril",
                     vigente_hasta=ahora_utc() - timedelta(minutes=5), estado="activo")
    db.add(charco)
    db.commit()
    d = detalle(client, charco.id).json()
    assert d["estado"] == "historico" and d["tipo_dano"] is None and d["nivel_agua"] == "cubre_carril"
    assert d["historial"][0]["estado_nuevo"] == "historico"


def test_inexistente_responde_404(client):
    r = detalle(client, 99999)
    assert r.status_code == 404 and r.json()["codigo"] == "NO_ENCONTRADO"


def test_las_rutas_fijas_no_se_confunden_con_un_id(client, ciudadano):
    assert client.get("/api/reportes/cercanos", headers=encabezado_de(ciudadano)).status_code == 422  # faltan lat/lon
    assert client.get("/api/reportes/baches").status_code == 405


@pytest.fixture()
def rechazado(db, catalogo, ciudadano, moderador):
    """Bache de `ciudadano` que un moderador rechazó desde «recibido»."""
    reporte = Reporte(folio="BCH-2026-000888", categoria="bache", tipo_dano_id=catalogo["tipos"]["bache"].id,
                      autor_id=ciudadano.id, colonia_id=catalogo["colonia"].id, calle="Calle", lat=31.7, lon=-106.4,
                      severidad="baja", tamano="chico", profundidad="baja", carril="orilla", estado="recibido")
    db.add(reporte)
    db.flush()
    registrar_cambio_estado(db, reporte, "rechazado", actor=moderador, motivo_texto="Prueba")
    db.commit()
    return reporte


def test_rechazado_es_404_para_el_publico_y_para_su_autor(client, rechazado, ciudadano):
    for usuario in (None, ciudadano):
        r = detalle(client, rechazado.id, usuario)
        assert r.status_code == 404 and r.json()["codigo"] == "NO_ENCONTRADO"


@pytest.mark.parametrize("rol", ["moderador", "coordinador"])
def test_rechazado_visible_para_moderacion(client, crear_usuario, rechazado, rol):
    usuario = crear_usuario(f"otro-{rol}@ejemplo.test", rol=rol)
    r = detalle(client, rechazado.id, usuario)
    assert r.status_code == 200 and r.json()["estado"] == "rechazado"
    assert not (llaves_de(r.json()) & LLAVES_PROHIBIDAS)


def test_longevidad_de_uno_abierto_cuenta_hasta_hoy(client, bache):
    d = detalle(client, bache.id).json()
    esperado = (hoy_local() - a_hora_local(bache.creado_en).date()).days
    assert d["longevidad_dias"] == d["antiguedad_dias"] == esperado
