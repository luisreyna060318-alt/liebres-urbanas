"""Máquina de estados de los reportes (RN-05 baches, RN-06 encharcamientos) y su historial.

REGLA: el estado de un reporte se cambia SOLO con registrar_cambio_estado(). Esa función valida el salto,
actualiza el reporte y agrega la fila del historial en la misma transacción; así el historial nunca se
desincroniza del estado.

Uso típico en un servicio (por ejemplo, validar un bache en C6):

    from app.services.estados import registrar_cambio_estado

    reporte = db.get(Reporte, reporte_id)
    registrar_cambio_estado(db, reporte, "validado", actor=moderador, comentario="Confirmado en sitio")
    db.commit()   # <- lo hace quien llama: si algo más falla antes, se deshace todo junto

Otros ejemplos:
    registrar_cambio_estado(db, r, "reparado", actor=k, fecha_reparacion=date(2026, 11, 20))
    registrar_cambio_estado(db, r, "rechazado", actor=m, motivo_rechazo_id=motivo.id, motivo_texto="...")
    registrar_cambio_estado(db, r, "historico", actor=None, comentario="Venció la vigencia")  # actor None = sistema

Quién puede hacer cada salto (moderador, coordinador) lo decide el router con require_role(); esta función
solo cuida que el salto exista. Al crear un reporte se usa registrar_estado_inicial().
"""

from datetime import date

from sqlalchemy.orm import Session

from app.core.errores import ErrorApi, error_validacion
from app.core.reglas import ESTADO_INICIAL
from app.core.tiempo import a_hora_local, hoy_local
from app.models import HistorialEstado, Reporte, Usuario

# Saltos permitidos: estado actual -> estados a los que puede pasar. Cualquier otro responde 409.
TRANSICIONES_BACHE: dict[str, set[str]] = {
    "recibido": {"validado", "rechazado"},  # moderador
    "validado": {"en_reparacion"},  # moderador o coordinador
    "en_reparacion": {"reparado"},  # moderador o coordinador, con fecha de reparación
    "reparado": set(),  # final
    "rechazado": set(),  # final
}
TRANSICIONES_ENCHARCAMIENTO: dict[str, set[str]] = {
    "activo": {"historico", "rechazado"},  # historico: 6 h sin confirmaciones o 3 desmentidos (sistema)
    "historico": {"rechazado"},  # el moderador puede rechazarlo en cualquier momento
    "rechazado": set(),
}
TRANSICIONES = {"bache": TRANSICIONES_BACHE, "encharcamiento": TRANSICIONES_ENCHARCAMIENTO}


def puede_pasar(categoria: str, estado_actual: str, estado_nuevo: str) -> bool:
    """True si RN-05/RN-06 permiten ese salto."""
    return estado_nuevo in TRANSICIONES.get(categoria, {}).get(estado_actual, set())


def _validar_fecha_reparacion(reporte: Reporte, fecha: date | None) -> None:
    """Reparado exige fecha: no futura ni anterior al día en que se reportó (hora de Juárez, HU-05.2)."""
    if fecha is None:
        raise error_validacion({"fecha_reparacion": "Indica la fecha en que se reparó"})
    if fecha > hoy_local():
        raise error_validacion({"fecha_reparacion": "La fecha de reparación no puede ser futura"})
    if fecha < a_hora_local(reporte.creado_en).date():
        raise error_validacion({"fecha_reparacion": "La fecha de reparación no puede ser anterior al reporte"})


def registrar_cambio_estado(
    db: Session,
    reporte: Reporte,
    nuevo_estado: str,
    actor: Usuario | None,
    comentario: str | None = None,
    *,
    fecha_reparacion: date | None = None,
    motivo_rechazo_id: int | None = None,
    motivo_texto: str | None = None,
) -> HistorialEstado:
    """Cambia el estado del reporte y agrega la fila del historial. Hace flush, NO commit.

    - 409 TRANSICION_INVALIDA si el salto no está en las tablas de arriba.
    - 422 VALIDACION (campo fecha_reparacion) si se pasa a "reparado" sin una fecha válida.
    - `actor=None` significa que el cambio lo hizo el sistema (vigencia de encharcamientos).
    - En "rechazado" guarda el motivo; que el motivo exista y que traiga texto cuando pide_explicacion
      lo valida el servicio de moderación antes de llamar aquí.
    """
    estado_anterior = reporte.estado
    if not puede_pasar(reporte.categoria, estado_anterior, nuevo_estado):
        raise ErrorApi(
            409, "TRANSICION_INVALIDA", f"Un reporte en «{estado_anterior}» no puede pasar a «{nuevo_estado}»"
        )

    if nuevo_estado == "reparado":
        _validar_fecha_reparacion(reporte, fecha_reparacion)
        reporte.fecha_reparacion = fecha_reparacion
    if nuevo_estado == "rechazado":
        reporte.motivo_rechazo_id = motivo_rechazo_id
        reporte.motivo_texto = motivo_texto

    reporte.estado = nuevo_estado
    fila = HistorialEstado(
        reporte=reporte,
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado,
        actor_id=actor.id if actor else None,
        comentario=comentario,
    )
    db.add(fila)
    db.flush()
    return fila


def registrar_estado_inicial(db: Session, reporte: Reporte, autor: Usuario) -> HistorialEstado:
    """Primera fila del historial al crear un reporte (estado_anterior = NULL). Hace flush, NO commit.

    Pone el estado inicial de la categoría (recibido o activo) si el reporte aún no lo trae.
    """
    if not reporte.estado:
        reporte.estado = ESTADO_INICIAL[reporte.categoria]
    fila = HistorialEstado(
        reporte=reporte, estado_anterior=None, estado_nuevo=reporte.estado, actor_id=autor.id, comentario=None
    )
    db.add(fila)
    db.flush()
    return fila
