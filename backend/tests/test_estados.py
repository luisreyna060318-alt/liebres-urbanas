"""Máquina de estados (RN-05, RN-06), fecha de reparación e historial inalterable (RN-07)."""

from datetime import timedelta

import pytest

from app.core.errores import ErrorApi
from app.core.tiempo import ahora_utc, hoy_local
from app.models import HistorialEstado, HistorialInalterable, Reporte
from app.services.estados import puede_pasar, registrar_cambio_estado, registrar_estado_inicial


def test_bache_recorre_todo_su_ciclo_y_queda_en_el_historial(db, crear_reporte, ciudadano, moderador):
    reporte = crear_reporte("bache")
    registrar_estado_inicial(db, reporte, ciudadano)
    registrar_cambio_estado(db, reporte, "validado", moderador, "Confirmado en sitio")
    registrar_cambio_estado(db, reporte, "en_reparacion", moderador)
    registrar_cambio_estado(db, reporte, "reparado", moderador, fecha_reparacion=hoy_local())
    db.commit()

    assert reporte.estado == "reparado" and reporte.fecha_reparacion == hoy_local()
    pasos = [(h.estado_anterior, h.estado_nuevo) for h in reporte.historial]
    assert pasos == [(None, "recibido"), ("recibido", "validado"), ("validado", "en_reparacion"),
                     ("en_reparacion", "reparado")]
    assert reporte.historial[1].comentario == "Confirmado en sitio"
    assert reporte.historial[1].actor_id == moderador.id


@pytest.mark.parametrize(
    "actual,nuevo",
    [
        ("recibido", "en_reparacion"),
        ("recibido", "reparado"),
        ("validado", "recibido"),
        ("validado", "rechazado"),
        ("en_reparacion", "validado"),
        ("reparado", "en_reparacion"),
        ("rechazado", "validado"),
        ("recibido", "historico"),  # estado de la otra categoría
        ("recibido", "inventado"),
    ],
)
def test_bache_saltos_invalidos_responden_409(db, crear_reporte, moderador, actual, nuevo):
    # El CHECK exige fecha de reparación en un bache reparado
    fecha = hoy_local() if actual == "reparado" else None
    reporte = crear_reporte("bache", estado=actual, fecha_reparacion=fecha)
    with pytest.raises(ErrorApi) as error:
        registrar_cambio_estado(db, reporte, nuevo, moderador, fecha_reparacion=hoy_local())
    assert error.value.status_code == 409 and error.value.codigo == "TRANSICION_INVALIDA"
    assert reporte.estado == actual
    assert db.query(HistorialEstado).count() == 0


def test_rechazar_bache_guarda_el_motivo(db, crear_reporte, moderador):
    reporte = crear_reporte("bache")
    registrar_cambio_estado(db, reporte, "rechazado", moderador, motivo_texto="Es un estacionamiento privado")
    db.commit()
    assert reporte.estado == "rechazado" and reporte.motivo_texto == "Es un estacionamiento privado"


@pytest.mark.parametrize(
    "actual,nuevo,valido",
    [
        ("activo", "historico", True),
        ("activo", "rechazado", True),
        ("historico", "rechazado", True),
        ("historico", "activo", False),
        ("rechazado", "activo", False),
        ("activo", "validado", False),
    ],
)
def test_transiciones_de_encharcamiento(actual, nuevo, valido):
    assert puede_pasar("encharcamiento", actual, nuevo) is valido


def test_encharcamiento_vence_por_el_sistema(db, crear_reporte):
    reporte = crear_reporte("encharcamiento")
    fila = registrar_cambio_estado(db, reporte, "historico", actor=None, comentario="Venció la vigencia")
    db.commit()
    assert reporte.estado == "historico"
    assert fila.actor_id is None  # NULL = sistema


@pytest.mark.parametrize(
    "dias,mensaje",
    [(None, "Indica la fecha"), (1, "no puede ser futura"), (-10, "no puede ser anterior")],
    ids=["sin-fecha", "futura", "antes-del-reporte"],
)
def test_reparado_exige_fecha_valida(db, crear_reporte, moderador, dias, mensaje):
    reporte = crear_reporte("bache", estado="en_reparacion", creado_en=ahora_utc() - timedelta(days=3))
    fecha = None if dias is None else hoy_local() + timedelta(days=dias)
    with pytest.raises(ErrorApi) as error:
        registrar_cambio_estado(db, reporte, "reparado", moderador, fecha_reparacion=fecha)
    assert error.value.status_code == 422 and error.value.codigo == "VALIDACION"
    assert mensaje in error.value.campos["fecha_reparacion"]
    assert reporte.estado == "en_reparacion"


def test_reparado_el_mismo_dia_del_reporte_es_valido(db, crear_reporte, moderador):
    reporte = crear_reporte("bache", estado="en_reparacion")
    registrar_cambio_estado(db, reporte, "reparado", moderador, fecha_reparacion=hoy_local())
    db.commit()
    assert reporte.estado == "reparado"


# --- Historial inalterable a nivel ORM ------------------------------------------------------------
def test_historial_no_se_puede_actualizar(db, crear_reporte, ciudadano):
    reporte = crear_reporte("bache")
    fila = registrar_estado_inicial(db, reporte, ciudadano)
    db.commit()
    fila.comentario = "texto cambiado"
    with pytest.raises(HistorialInalterable):
        db.flush()
    db.rollback()


def test_historial_no_se_puede_borrar(db, crear_reporte, ciudadano):
    reporte = crear_reporte("bache")
    fila = registrar_estado_inicial(db, reporte, ciudadano)
    db.commit()
    db.delete(fila)
    with pytest.raises(HistorialInalterable):
        db.flush()
    db.rollback()


def test_borrar_un_reporte_completo_borra_su_historial_en_cascada(db, crear_reporte, ciudadano):
    """HU-02.5: el autor puede borrar un reporte en "recibido"; la base borra su historial (ON DELETE CASCADE)."""
    reporte = crear_reporte("bache")
    registrar_estado_inicial(db, reporte, ciudadano)
    db.commit()
    db.delete(reporte)
    db.commit()
    assert db.query(Reporte).count() == 0
    assert db.query(HistorialEstado).count() == 0
