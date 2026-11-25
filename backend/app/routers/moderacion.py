"""Rutas de moderación (HU-05.1). Sin lógica: reciben, llaman al servicio y responden.

Solo el rol moderador (tabla de endpoints #26 a #28 de DISENO_TECNICO); el coordinador recibe 403.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import SesionDB, require_role
from app.models import Usuario
from app.schemas.comun import Pagina, respuestas_error
from app.schemas.moderacion import RechazarEntrada, ValidarEntrada
from app.schemas.reportes import ReportePublico
from app.services import moderacion as moderacion_service

router = APIRouter(prefix="/api", tags=["Moderación"])

Moderador = Annotated[Usuario, Depends(require_role("moderador"))]

ERRORES_CAMBIO = {
    **respuestas_error(401, 403, 404, 422),
    409: {"description": "`TRANSICION_INVALIDA`: el reporte no está en un estado que permita ese cambio"},
}


@router.get(
    "/moderacion/bandeja",
    response_model=Pagina[ReportePublico],
    summary="Bandeja de reportes por revisar",
    responses=respuestas_error(401, 403, 422),
)
def bandeja(
    usuario: Moderador,
    db: SesionDB,
    colonia_id: int | None = Query(None, description="Solo los de esta colonia"),
    tipo_dano_codigo: str | None = Query(None, max_length=40, description="bache, hundimiento, grieta..."),
    pagina: int = Query(1, ge=1, description="Empieza en 1"),
):
    """Baches en **recibido**, del más antiguo al más reciente, **10 por página**. Sin datos del autor."""
    return moderacion_service.listar_bandeja(db, colonia_id, tipo_dano_codigo, pagina)


@router.post(
    "/reportes/{reporte_id}/validar", response_model=ReportePublico, summary="Validar un bache",
    responses=ERRORES_CAMBIO,
)
def validar(reporte_id: int, datos: ValidarEntrada, usuario: Moderador, db: SesionDB):
    """**recibido → validado**. El historial guarda quién, cuándo y el comentario (opcional y público)."""
    return moderacion_service.validar(db, usuario, reporte_id, datos)


@router.post(
    "/reportes/{reporte_id}/rechazar", response_model=ReportePublico, summary="Rechazar un reporte",
    responses=ERRORES_CAMBIO,
)
def rechazar(reporte_id: int, datos: RechazarEntrada, usuario: Moderador, db: SesionDB):
    """Rechaza un bache en **recibido** o un encharcamiento **activo** o **histórico** (RN-06).

    `motivo_rechazo_id` es obligatorio y debe estar activo; si el motivo tiene `pide_explicacion`,
    `motivo_texto` también. El autor ve el motivo en «Mis reportes»."""
    return moderacion_service.rechazar(db, usuario, reporte_id, datos)
