"""Rutas de reportes del ciudadano. Sin lógica: reciben, llaman al servicio y responden.

Nota para quien agregue GET /api/reportes/{id}: las rutas fijas (/baches, /cercanos...) deben registrarse
antes que las de {id}, o declarar el id como entero, para que "cercanos" no se confunda con un id.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import SesionDB, require_role
from app.core.reglas import CATEGORIAS
from app.models import Usuario
from app.schemas.comun import respuestas_error
from app.schemas.reportes import BacheEntrada, Cercano, ConfirmacionEntrada, ReporteMio, ReportePublico
from app.services import cercanos as cercanos_service
from app.services import confirmaciones as confirmaciones_service
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


@router.get(
    "/reportes/cercanos",
    response_model=list[Cercano],
    summary="Reportes cercanos a un punto",
    responses=respuestas_error(401, 403, 422),
)
def reportes_cercanos(
    usuario: Ciudadano,
    db: SesionDB,
    categoria: Literal[CATEGORIAS] = Query(description="bache (radio 30 m) o encharcamiento (radio 50 m)"),
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
):
    """Baches abiertos a 30 m o menos, o encharcamientos activos y vigentes a 50 m o menos, del más cercano al más
    lejano. El formulario lo llama antes de enviar para ofrecer «confirmar» en lugar de duplicar (HU-02.3)."""
    return cercanos_service.cercanos_publicos(db, categoria, lat, lon)


@router.post(
    "/reportes/{reporte_id}/confirmaciones",
    response_model=ReportePublico,
    status_code=status.HTTP_201_CREATED,
    summary="Confirmar un reporte",
    responses={
        **respuestas_error(401, 403, 404, 422),
        403: {"description": "`SIN_PERMISO` (rol) o `ES_TU_REPORTE` (es tu propio reporte)"},
        409: {"description": "`YA_CONFIRMADO` o `TRANSICION_INVALIDA` (el reporte ya está cerrado)"},
    },
)
def confirmar_reporte(reporte_id: int, datos: ConfirmacionEntrada, usuario: Ciudadano, db: SesionDB):
    """Suma tu confirmación a un reporte existente sin crear otro folio.

    - `confirma`: solo baches abiertos; suma 1 a `confirmaciones`.
    Una respuesta por persona y por reporte; el autor no puede confirmar el suyo."""
    return confirmaciones_service.confirmar(db, usuario, reporte_id, datos.tipo)
