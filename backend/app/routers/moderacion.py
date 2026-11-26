"""Rutas de moderación (HU-05.1) y del avance de reparación (HU-05.2). Sin lógica: reciben, llaman al servicio
y responden.

Bandeja, validar y rechazar: solo el rol moderador (tabla de endpoints #26 a #28 de DISENO_TECNICO); el coordinador
recibe 403. Avance de la reparación y su listado: moderador o coordinador (#29).
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.core.deps import SesionDB, require_role
from app.core.reglas import PAGINA_MAX
from app.models import Usuario
from app.schemas.comun import Pagina, respuestas_error
from app.schemas.moderacion import AvanceEntrada, RechazarEntrada, ValidarEntrada
from app.schemas.reportes import ReportePublico
from app.services import moderacion as moderacion_service

router = APIRouter(prefix="/api", tags=["Moderación"])

Moderador = Annotated[Usuario, Depends(require_role("moderador"))]
ModeradorOCoordinador = Annotated[Usuario, Depends(require_role("moderador", "coordinador"))]

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
    pagina: int = Query(1, ge=1, le=PAGINA_MAX, description="Empieza en 1"),
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


# --- Avance de la reparación (HU-05.2, endpoint #29): moderador o coordinador --------------------------
@router.get(
    "/moderacion/seguimiento",
    response_model=Pagina[ReportePublico],
    summary="Baches en seguimiento",
    responses=respuestas_error(401, 403, 422),
)
def seguimiento(
    usuario: ModeradorOCoordinador,
    db: SesionDB,
    estado: Literal["validado", "en_reparacion"] | None = Query(None, description="Vacío = los dos"),
    colonia_id: int | None = Query(None, description="Solo los de esta colonia"),
    tipo_dano_codigo: str | None = Query(None, max_length=40, description="bache, hundimiento, grieta..."),
    pagina: int = Query(1, ge=1, le=PAGINA_MAX, description="Empieza en 1"),
):
    """Baches **validados** y **en reparación**, del más antiguo al más reciente, **10 por página**."""
    return moderacion_service.listar_seguimiento(db, estado, colonia_id, tipo_dano_codigo, pagina)


@router.post(
    "/reportes/{reporte_id}/estado", response_model=ReportePublico, summary="Registrar el avance de una reparación",
    responses=ERRORES_CAMBIO,
)
def registrar_avance(reporte_id: int, datos: AvanceEntrada, usuario: ModeradorOCoordinador, db: SesionDB):
    """**validado → en_reparacion → reparado** (RN-05); cualquier otro salto → 409 `TRANSICION_INVALIDA`.

    `reparado` exige `fecha_reparacion` (ni futura ni anterior al día del reporte, 422 en `campos`).
    El `comentario` es público y aparece en el historial del detalle. El historial no se modifica ni se borra."""
    return moderacion_service.registrar_avance(db, usuario, reporte_id, datos)
