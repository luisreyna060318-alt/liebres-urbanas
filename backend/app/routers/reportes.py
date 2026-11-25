"""Rutas de reportes del ciudadano. Sin lógica: reciben, llaman al servicio y responden.

Nota para quien agregue GET /api/reportes/{id}: las rutas fijas (/baches, /cercanos...) deben registrarse
antes que las de {id}, o declarar el id como entero, para que "cercanos" no se confunda con un id.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import SesionDB, require_role
from app.models import Usuario
from app.schemas.comun import respuestas_error
from app.schemas.reportes import BacheEntrada, ReporteMio
from app.services import reportes as reportes_service

router = APIRouter(prefix="/api", tags=["Reportes del ciudadano"])

# Solo el rol ciudadano crea y confirma reportes (moderador y coordinador -> 403 SIN_PERMISO)
Ciudadano = Annotated[Usuario, Depends(require_role("ciudadano"))]

ERRORES_ALTA = {
    **respuestas_error(401, 403, 422),
    409: {"description": "`POSIBLE_DUPLICADO`: hay un reporte cercano (incluye `duplicados`)"},
    429: {"description": "`LIMITE_HORARIO`: más de 10 reportes en una hora"},
}


@router.post(
    "/reportes/baches",
    response_model=ReporteMio,
    status_code=status.HTTP_201_CREATED,
    summary="Reportar un bache",
    responses=ERRORES_ALTA,
)
def crear_bache(datos: BacheEntrada, usuario: Ciudadano, db: SesionDB):
    """Crea un bache en estado **recibido** con folio `BCH-AAAA-NNNNNN` y fecha del servidor.

    Campos por tipo de daño (HU-02.2):
    - `bache`: `tamano`, `profundidad` y `carril`.
    - `hundimiento` y `grieta`: `tamano` y `carril`.
    - `alcantarilla_sin_tapa`: `senalizado`; la severidad queda en **alta**.

    La severidad la calcula el servidor. Fuera de Juárez → 422 `FUERA_DEL_MUNICIPIO`."""
    return reportes_service.crear_bache(db, usuario, datos)
