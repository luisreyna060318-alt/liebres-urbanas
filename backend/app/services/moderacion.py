"""Moderación: bandeja de reportes nuevos, validar y rechazar (HU-05.1).

Los cambios de estado pasan SIEMPRE por registrar_cambio_estado() (services/estados.py), que valida el salto y
agrega la fila del historial con el actor, la fecha y el comentario. El historial interno guarda quién hizo el
cambio; el historial público (ReporteDetalle) no lo muestra (RN-04).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.errores import ErrorApi, error_validacion
from app.core.paginacion import paginar
from app.core.reglas import TAM_PAGINA_MODERACION
from app.core.tiempo import hoy_local
from app.models import MotivoRechazo, Reporte, TipoDano, Usuario
from app.schemas.moderacion import RechazarEntrada, ValidarEntrada
from app.schemas.reportes import ReportePublico, a_reporte_publico
from app.services.encharcamientos import expirar_vencidos
from app.services.estados import puede_pasar, registrar_cambio_estado

# Nombres para los mensajes de error (la API guarda los estados sin acentos)
NOMBRE_ESTADO = {
    "recibido": "Recibido",
    "validado": "Validado",
    "en_reparacion": "En reparación",
    "reparado": "Reparado",
    "rechazado": "Rechazado",
    "activo": "Activo",
    "historico": "Histórico",
}


def consulta_de_baches(estados: tuple[str, ...], colonia_id: int | None, tipo_dano_codigo: str | None):
    """Baches en esos estados, del MÁS ANTIGUO al más reciente (así se atiende primero lo que lleva más tiempo).
    Filtros opcionales por colonia y por tipo de daño. También la usa el seguimiento de reparaciones."""
    consulta = (
        select(Reporte)
        .options(joinedload(Reporte.tipo_dano), joinedload(Reporte.colonia))
        .where(Reporte.categoria == "bache", Reporte.estado.in_(estados))
        .order_by(Reporte.creado_en, Reporte.id)
    )
    if colonia_id is not None:
        consulta = consulta.where(Reporte.colonia_id == colonia_id)
    if tipo_dano_codigo:
        # Parámetro de SQLAlchemy: el texto del filtro nunca se pega a mano en el SQL
        consulta = consulta.join(TipoDano, Reporte.tipo_dano_id == TipoDano.id).where(
            TipoDano.codigo == tipo_dano_codigo
        )
    return consulta


def paginar_publicos(db: Session, consulta, pagina: int) -> dict:
    """Pagina la consulta (10 por página) y convierte cada reporte a ReportePublico (sin autor)."""
    resultado = paginar(db, consulta, pagina, TAM_PAGINA_MODERACION)
    hoy = hoy_local()
    resultado["items"] = [a_reporte_publico(r, hoy) for r in resultado["items"]]
    return resultado


def listar_bandeja(db: Session, colonia_id: int | None, tipo_dano_codigo: str | None, pagina: int) -> dict:
    """GET /api/moderacion/bandeja: baches en «recibido» que esperan revisión."""
    expirar_vencidos(db)
    return paginar_publicos(db, consulta_de_baches(("recibido",), colonia_id, tipo_dano_codigo), pagina)


def obtener_reporte(db: Session, reporte_id: int) -> Reporte:
    """El reporte o 404 NO_ENCONTRADO."""
    reporte = db.get(Reporte, reporte_id)
    if reporte is None:
        raise ErrorApi(404, "NO_ENCONTRADO", "El reporte no existe")
    return reporte


def exigir_salto(reporte: Reporte, nuevo_estado: str, explicacion: str) -> None:
    """409 TRANSICION_INVALIDA con un mensaje claro ANTES de revisar el resto de los datos (RN-05 y RN-06).
    registrar_cambio_estado() lo vuelve a revisar; aquí solo se adelanta para explicar mejor el porqué."""
    if not puede_pasar(reporte.categoria, reporte.estado, nuevo_estado):
        actual = NOMBRE_ESTADO.get(reporte.estado, reporte.estado)
        raise ErrorApi(409, "TRANSICION_INVALIDA", f"El reporte {reporte.folio} está en «{actual}»: {explicacion}")


def validar(db: Session, moderador: Usuario, reporte_id: int, datos: ValidarEntrada) -> ReportePublico:
    """recibido -> validado. Queda en el historial con el moderador, la fecha y hora y el comentario."""
    expirar_vencidos(db)
    reporte = obtener_reporte(db, reporte_id)
    exigir_salto(reporte, "validado", "solo se validan baches que siguen en «Recibido»")
    registrar_cambio_estado(db, reporte, "validado", actor=moderador, comentario=datos.comentario)
    db.commit()
    return a_reporte_publico(reporte, hoy_local())


def _motivo_valido(db: Session, datos: RechazarEntrada) -> MotivoRechazo:
    """El motivo debe existir y estar activo; si pide explicación, el texto es obligatorio (422 por campo)."""
    motivo = db.get(MotivoRechazo, datos.motivo_rechazo_id)
    if motivo is None or not motivo.activo:
        raise error_validacion({"motivo_rechazo_id": "Elige un motivo de la lista"})
    if motivo.pide_explicacion and not datos.motivo_texto:
        raise error_validacion({"motivo_texto": f"Explica el motivo «{motivo.nombre}»"})
    return motivo


def rechazar(db: Session, moderador: Usuario, reporte_id: int, datos: RechazarEntrada) -> ReportePublico:
    """Rechaza un bache en «recibido», o un encharcamiento activo o histórico en cualquier momento (RN-06).
    El autor ve el motivo y la explicación en «Mis reportes» (ReporteMio.motivo_rechazo)."""
    expirar_vencidos(db)
    reporte = obtener_reporte(db, reporte_id)
    exigir_salto(
        reporte, "rechazado", "solo se rechazan baches en «Recibido» y encharcamientos que no estén rechazados"
    )
    motivo = _motivo_valido(db, datos)
    registrar_cambio_estado(
        db, reporte, "rechazado", actor=moderador, comentario=datos.comentario,
        motivo_rechazo_id=motivo.id, motivo_texto=datos.motivo_texto,
    )
    db.commit()
    return a_reporte_publico(reporte, hoy_local())
