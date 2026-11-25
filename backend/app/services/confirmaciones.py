"""Confirmar un reporte existente en lugar de duplicarlo (HU-02.3; los tipos del encharcamiento, HU-03.3).

Reglas comunes:
- Una persona responde UNA sola vez por reporte (restricción única en la base) -> 409 YA_CONFIRMADO.
- El autor no responde sobre su propio reporte -> 403 ES_TU_REPORTE.
- Un reporte inexistente o rechazado (no visible al público) -> 404 NO_ENCONTRADO.
- Un tipo que no corresponde a la categoría -> 422 VALIDACION.
- Un reporte ya cerrado (bache reparado, encharcamiento «historico») -> 409 TRANSICION_INVALIDA: ya no admite
  respuestas. Se eligió 409 y no 404 porque el reporte sí existe y se sigue viendo en la consulta (histórico).
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errores import ErrorApi, error_validacion
from app.core.tiempo import a_hora_local, ahora_utc
from app.models import Confirmacion, Reporte, Usuario
from app.schemas.reportes import ESTADOS_BACHE_ABIERTOS, ReportePublico, a_reporte_publico
from app.services.encharcamientos import aplicar_respuesta, expirar_vencidos

# Qué respuestas admite cada categoría
TIPOS_POR_CATEGORIA: dict[str, tuple[str, ...]] = {
    "bache": ("confirma",),
    "encharcamiento": ("sigue", "ya_no_hay"),
}


def _ya_confirmado() -> ErrorApi:
    return ErrorApi(409, "YA_CONFIRMADO", "Ya respondiste sobre este reporte. Gracias por tu ayuda")


def confirmar(
    db: Session, usuario: Usuario, reporte_id: int, tipo: str, ahora: datetime | None = None
) -> ReportePublico:
    """Registra la respuesta de `usuario` sobre el reporte y devuelve el reporte actualizado. Hace commit."""
    ahora = ahora or ahora_utc()
    expirar_vencidos(db, ahora)  # un encharcamiento vencido ya no admite «sigue ahí»
    reporte = db.get(Reporte, reporte_id)
    if reporte is None or reporte.estado == "rechazado":
        raise ErrorApi(404, "NO_ENCONTRADO", "El reporte no existe")

    validos = TIPOS_POR_CATEGORIA[reporte.categoria]
    if tipo not in validos:
        opciones = ", ".join(validos)
        raise error_validacion({"tipo": f"Respuesta no válida para un {reporte.categoria}. Opciones: {opciones}"})
    if reporte.autor_id == usuario.id:
        raise ErrorApi(403, "ES_TU_REPORTE", "No puedes confirmar tu propio reporte")
    if reporte.categoria == "bache" and reporte.estado not in ESTADOS_BACHE_ABIERTOS:
        raise ErrorApi(409, "TRANSICION_INVALIDA", "Este bache ya está cerrado y no admite confirmaciones")
    if reporte.categoria == "encharcamiento" and reporte.estado != "activo":
        raise ErrorApi(409, "TRANSICION_INVALIDA", "Este encharcamiento ya no está activo y no admite respuestas")

    ya = db.scalar(
        select(Confirmacion).where(Confirmacion.reporte_id == reporte.id, Confirmacion.usuario_id == usuario.id)
    )
    if ya is not None:
        raise _ya_confirmado()

    # La respuesta queda guardada con su fecha y hora (HU-03.3: «ya no hay agua» con fecha y hora)
    db.add(Confirmacion(reporte_id=reporte.id, usuario_id=usuario.id, tipo=tipo, creado_en=ahora))
    try:
        db.flush()
    except IntegrityError:
        # Dos clics simultáneos de la misma persona: la restricción única de la base detiene el segundo
        db.rollback()
        raise _ya_confirmado() from None

    if tipo == "confirma":
        # Se suma en SQL (confirmaciones = confirmaciones + 1) para no perder una si dos llegan a la vez
        reporte.confirmaciones = Reporte.confirmaciones + 1
    else:
        aplicar_respuesta(db, reporte, tipo, ahora)  # «sigue» o «ya_no_hay»
    db.commit()
    db.refresh(reporte)
    return a_reporte_publico(reporte, a_hora_local(ahora).date())
