"""Tablero de indicadores (HU-07.1). Solo coordinador. Sin lógica: recibe el filtro y llama al servicio."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import SesionDB, require_role
from app.models import Usuario
from app.schemas.comun import IdEntero, respuestas_error
from app.schemas.tablero import TableroSalida
from app.services import tablero as tablero_service

router = APIRouter(prefix="/api", tags=["Tablero"])


@router.get(
    "/tablero",
    response_model=TableroSalida,
    summary="Tablero de indicadores",
    responses=respuestas_error(401, 403, 422),
)
def ver_tablero(
    db: SesionDB,
    _coordinador: Annotated[Usuario, Depends(require_role("coordinador"))],
    desde: Annotated[date | None, Query(description="AAAA-MM-DD, día de Ciudad Juárez (incluido)")] = None,
    hasta: Annotated[date | None, Query(description="AAAA-MM-DD, día de Ciudad Juárez (incluido)")] = None,
    sector_id: Annotated[IdEntero | None, Query(description="Solo las colonias de este sector")] = None,
):
    """Totales por tipo y estado, top 10 colonias, tiempo de reparación, reportes por semana y longevidad.

    Usa la misma función de filtrado que `GET /api/reportes`, así las cifras coinciden con la lista.
    `desde` > `hasta` o un sector inexistente → 422 `VALIDACION`."""
    return tablero_service.obtener_tablero(db, desde, hasta, sector_id)
