"""Avance de la reparación (HU-05.2): máquina de estados RN-05, fecha de reparación, comentario público,
historial inalterable y roles."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.tiempo import ahora_utc, hoy_local
from app.main import app
from app.models import HistorialEstado, HistorialInalterable
from app.schemas.reportes import a_reporte_detalle
from tests.conftest import LLAVES_PROHIBIDAS, encabezado_de, llaves_de

SEGUIMIENTO = "/api/moderacion/seguimiento"


def avanzar(client, usuario, reporte_id, **cuerpo):
    return client.post(f"/api/reportes/{reporte_id}/estado", json=cuerpo, headers=encabezado_de(usuario))


def filas_de(db, reporte):
    return list(db.scalars(select(HistorialEstado).where(HistorialEstado.reporte_id == reporte.id)))


# --- Transiciones válidas -------------------------------------------------------------------------
def test_validado_pasa_a_en_reparacion_con_comentario_publico(client, db, crear_reporte, moderador):
    reporte = crear_reporte("bache", estado="validado")
    r = avanzar(client, moderador, reporte.id, estado="en_reparacion", comentario="Cuadrilla asignada")
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "en_reparacion" and r.json()["fecha_reparacion"] is None
    assert not (llaves_de(r.json()) & LLAVES_PROHIBIDAS)

    fila = filas_de(db, reporte)[0]
    assert (fila.estado_anterior, fila.estado_nuevo, fila.actor_id) == ("validado", "en_reparacion", moderador.id)

    # El comentario aparece en el historial público del detalle, sin decir quién hizo el cambio
    detalle = a_reporte_detalle(reporte, hoy_local()).model_dump(mode="json")
    assert detalle["historial"][0]["comentario"] == "Cuadrilla asignada"
    assert not (llaves_de(detalle) & LLAVES_PROHIBIDAS)


def test_en_reparacion_pasa_a_reparado_con_fecha(client, db, crear_reporte, coordinador):
    reporte = crear_reporte("bache", estado="en_reparacion", creado_en=ahora_utc() - timedelta(days=4))
    ayer = hoy_local() - timedelta(days=1)
    r = avanzar(client, coordinador, reporte.id, estado="reparado", fecha_reparacion=ayer.isoformat())
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "reparado" and r.json()["fecha_reparacion"] == ayer.isoformat()
    assert r.json()["antiguedad_dias"] == 3  # RN-10: se cuenta hasta la reparación
    assert filas_de(db, reporte)[0].actor_id == coordinador.id


def test_la_fecha_se_ignora_al_pasar_a_en_reparacion(client, crear_reporte, moderador):
    reporte = crear_reporte("bache", estado="validado")
    r = avanzar(client, moderador, reporte.id, estado="en_reparacion", fecha_reparacion=hoy_local().isoformat())
    assert r.status_code == 200 and r.json()["fecha_reparacion"] is None


# --- Transiciones inválidas (409) -----------------------------------------------------------------
@pytest.mark.parametrize(
    "actual,nuevo",
    [("recibido", "en_reparacion"), ("recibido", "reparado"), ("validado", "reparado"),
     ("en_reparacion", "en_reparacion"), ("reparado", "en_reparacion"), ("rechazado", "en_reparacion")],
)
def test_saltos_invalidos_responden_409_con_mensaje_claro(client, db, crear_reporte, moderador, actual, nuevo):
    fecha = hoy_local() if actual == "reparado" else None  # el CHECK exige fecha en un bache reparado
    reporte = crear_reporte("bache", estado=actual, fecha_reparacion=fecha)
    r = avanzar(client, moderador, reporte.id, estado=nuevo, fecha_reparacion=hoy_local().isoformat())
    assert r.status_code == 409 and r.json()["codigo"] == "TRANSICION_INVALIDA"
    assert reporte.folio in r.json()["detail"] and "«Validado» a «En reparación»" in r.json()["detail"]
    db.refresh(reporte)
    assert reporte.estado == actual and filas_de(db, reporte) == []


def test_un_encharcamiento_no_registra_avance(client, crear_reporte, moderador):
    reporte = crear_reporte("encharcamiento")
    r = avanzar(client, moderador, reporte.id, estado="en_reparacion")
    assert r.status_code == 409


def test_estado_no_permitido_en_la_entrada_responde_422(client, crear_reporte, moderador):
    reporte = crear_reporte("bache", estado="recibido")
    r = avanzar(client, moderador, reporte.id, estado="validado")
    assert r.status_code == 422 and "estado" in r.json()["campos"]


def test_reporte_inexistente_responde_404(client, moderador):
    assert avanzar(client, moderador, 9999, estado="en_reparacion").status_code == 404


# --- Fecha de reparación (422 con campos) ---------------------------------------------------------
@pytest.mark.parametrize(
    "dias,mensaje",
    [(None, "Indica la fecha"), (1, "no puede ser futura"), (-10, "no puede ser anterior")],
    ids=["sin-fecha", "futura", "antes-del-reporte"],
)
def test_reparado_exige_fecha_valida(client, db, crear_reporte, moderador, dias, mensaje):
    reporte = crear_reporte("bache", estado="en_reparacion", creado_en=ahora_utc() - timedelta(days=3))
    cuerpo = {"estado": "reparado"}
    if dias is not None:
        cuerpo["fecha_reparacion"] = (hoy_local() + timedelta(days=dias)).isoformat()
    r = avanzar(client, moderador, reporte.id, **cuerpo)
    assert r.status_code == 422 and r.json()["codigo"] == "VALIDACION"
    assert mensaje in r.json()["campos"]["fecha_reparacion"]
    db.refresh(reporte)
    assert reporte.estado == "en_reparacion" and filas_de(db, reporte) == []


def test_comentario_de_mas_de_500_caracteres_responde_422(client, crear_reporte, moderador):
    reporte = crear_reporte("bache", estado="validado")
    r = avanzar(client, moderador, reporte.id, estado="en_reparacion", comentario="x" * 501)
    assert r.status_code == 422 and "comentario" in r.json()["campos"]


# --- Historial inalterable (HU-05.2 CA4) ----------------------------------------------------------
def test_ninguna_ruta_modifica_ni_borra_el_historial():
    rutas = app.openapi()["paths"]
    assert not [ruta for ruta in rutas if "historial" in ruta]
    # Sobre reportes, las únicas rutas con PUT, PATCH o DELETE son las del autor en «recibido» (HU-02.5)
    escrituras = {(m, ruta) for ruta, metodos in rutas.items() if ruta.startswith("/api/reportes")
                  for m in metodos if m in ("put", "patch", "delete")}
    assert escrituras == {("put", "/api/reportes/{reporte_id}"), ("delete", "/api/reportes/{reporte_id}")}


def test_el_orm_impide_cambiar_o_borrar_el_historial_de_un_avance(client, db, crear_reporte, moderador):
    reporte = crear_reporte("bache", estado="validado")
    assert avanzar(client, moderador, reporte.id, estado="en_reparacion", comentario="Original").status_code == 200
    fila = filas_de(db, reporte)[0]

    fila.comentario = "Comentario cambiado"
    with pytest.raises(HistorialInalterable):
        db.flush()
    db.rollback()

    db.delete(fila)
    with pytest.raises(HistorialInalterable):
        db.flush()
    db.rollback()
    assert filas_de(db, reporte)[0].comentario == "Original"


# --- Listado de seguimiento -----------------------------------------------------------------------
def test_seguimiento_lista_validados_y_en_reparacion_del_mas_antiguo(client, crear_reporte, moderador):
    nuevo = crear_reporte("bache", estado="validado")
    viejo = crear_reporte("bache", estado="en_reparacion", creado_en=ahora_utc() - timedelta(days=5))
    crear_reporte("bache", estado="recibido")
    crear_reporte("bache", estado="reparado", fecha_reparacion=hoy_local())
    crear_reporte("encharcamiento")

    r = client.get(SEGUIMIENTO, headers=encabezado_de(moderador))
    assert r.status_code == 200
    assert [i["folio"] for i in r.json()["items"]] == [viejo.folio, nuevo.folio]
    assert r.json()["tam"] == 10
    assert not (llaves_de(r.json()) & LLAVES_PROHIBIDAS)

    solo = client.get(SEGUIMIENTO, params={"estado": "validado"}, headers=encabezado_de(moderador))
    assert [i["folio"] for i in solo.json()["items"]] == [nuevo.folio]
    assert client.get(SEGUIMIENTO, params={"estado": "reparado"}, headers=encabezado_de(moderador)).status_code == 422


def test_seguimiento_pagina_de_10_en_10(client, crear_reporte, coordinador):
    for i in range(11):
        crear_reporte("bache", estado="validado", creado_en=ahora_utc() - timedelta(days=20 - i))
    segunda = client.get(SEGUIMIENTO, params={"pagina": 2}, headers=encabezado_de(coordinador)).json()
    assert segunda["total"] == 11 and len(segunda["items"]) == 1


# --- Roles ----------------------------------------------------------------------------------------
def test_roles_del_avance(client, crear_reporte, ciudadano, moderador, coordinador):
    reporte = crear_reporte("bache", estado="validado")
    assert client.post(f"/api/reportes/{reporte.id}/estado", json={"estado": "en_reparacion"}).status_code == 401
    r = avanzar(client, ciudadano, reporte.id, estado="en_reparacion")
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    assert avanzar(client, moderador, reporte.id, estado="en_reparacion").status_code == 200
    r = avanzar(client, coordinador, reporte.id, estado="reparado", fecha_reparacion=hoy_local().isoformat())
    assert r.status_code == 200


def test_roles_del_seguimiento(client, ciudadano, moderador, coordinador):
    assert client.get(SEGUIMIENTO).status_code == 401
    assert client.get(SEGUIMIENTO, headers=encabezado_de(ciudadano)).status_code == 403
    assert client.get(SEGUIMIENTO, headers=encabezado_de(moderador)).status_code == 200
    assert client.get(SEGUIMIENTO, headers=encabezado_de(coordinador)).status_code == 200
