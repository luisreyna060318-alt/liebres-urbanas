"""Rutas de reportes del ciudadano. Sin lógica: reciben, llaman al servicio y responden.

Nota para quien agregue GET /api/reportes/{id}: las rutas fijas (/baches, /cercanos...) deben registrarse
antes que las de {id}, o declarar el id como entero, para que "cercanos" no se confunda con un id.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import SesionDB, require_role
from app.core.reglas import CATEGORIAS, PAGINA_MAX
from app.models import Usuario
from app.schemas.comun import IdEntero, Pagina, respuestas_error
from app.schemas.reportes import (
    BacheEdicion,
    BacheEntrada,
    Cercano,
    ConfirmacionEntrada,
    EncharcamientoEntrada,
    ReporteMio,
    ReportePublico,
)
from app.services import confirmaciones as confirmaciones_service
from app.services import encharcamientos as encharcamientos_service
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


@router.post(
    "/reportes/encharcamientos",
    response_model=ReporteMio,
    status_code=status.HTTP_201_CREATED,
    summary="Reportar un encharcamiento",
    responses=ERRORES_ALTA,
)
def crear_encharcamiento(datos: EncharcamientoEntrada, usuario: Ciudadano, db: SesionDB):
    """Crea un encharcamiento que se publica **activo** de inmediato (RN-06), con folio `ENC-AAAA-NNNNNN` y
    `vigente_hasta` = ahora + 6 h.

    - `nivel_agua`: `a_un_lado`, `cubre_carril`, `media_llanta` o `intransitable`.
    - `intransitable` exige `hay_riesgo` (¿vehículos varados o personas en riesgo?).
    - Si hay uno activo a 50 m o menos → 409 `POSIBLE_DUPLICADO` (reenvía con `forzar: true` para crearlo)."""
    return encharcamientos_service.crear_encharcamiento(db, usuario, datos)


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
    return reportes_service.cercanos_para_formulario(db, categoria, lat, lon)


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
def confirmar_reporte(reporte_id: IdEntero, datos: ConfirmacionEntrada, usuario: Ciudadano, db: SesionDB):
    """Suma tu confirmación a un reporte existente sin crear otro folio.

    - `confirma`: solo baches abiertos; suma 1 a `confirmaciones`.
    - `sigue`: solo encharcamientos activos; la vigencia pasa a 6 h **desde este momento** y suma 1.
    - `ya_no_hay`: solo encharcamientos activos; con el tercer desmentido de personas distintas pasa a «historico».
    Una respuesta por persona y por reporte; el autor no puede confirmar el suyo."""
    return confirmaciones_service.confirmar(db, usuario, reporte_id, datos.tipo)


ERRORES_AUTOR = {
    **respuestas_error(401, 403, 404),
    403: {"description": "`SIN_PERMISO`: no eres el autor (o tu rol no es ciudadano)"},
    409: {"description": "`REPORTE_NO_EDITABLE`: el reporte ya no está en «recibido»"},
}


@router.get(
    "/mis-reportes",
    response_model=Pagina[ReporteMio],
    summary="Mis reportes",
    responses=respuestas_error(401, 403, 422),
)
def mis_reportes(
    usuario: Ciudadano, db: SesionDB, pagina: int = Query(1, ge=1, le=PAGINA_MAX, description="Empieza en 1")
):
    """Tus baches y encharcamientos, **10 por página**, del más reciente al más antiguo.

    `puede_editar` es `true` solo en «recibido»; si un moderador lo rechazó, `motivo_rechazo` dice por qué.
    Si `total` es 0, la interfaz invita a crear el primer reporte (HU-02.5 CA4)."""
    return reportes_service.listar_mis_reportes(db, usuario, pagina)


@router.put(
    "/reportes/{reporte_id}",
    response_model=ReporteMio,
    summary="Corregir mi reporte",
    responses={**ERRORES_AUTOR, **respuestas_error(422)},
)
def editar_reporte(reporte_id: IdEntero, datos: BacheEdicion, usuario: Ciudadano, db: SesionDB):
    """Corrige un bache **propio** mientras siga en «recibido». Mismos campos y validaciones del alta, sin `forzar`.
    Los encharcamientos se publican activos de inmediato y no se editan (409)."""
    return reportes_service.editar_bache(db, usuario, reporte_id, datos)


@router.delete(
    "/reportes/{reporte_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar mi reporte",
    responses=ERRORES_AUTOR,
)
def eliminar_reporte(reporte_id: IdEntero, usuario: Ciudadano, db: SesionDB):
    """Elimina un reporte **propio** mientras siga en «recibido» (204, sin cuerpo)."""
    reportes_service.eliminar_reporte(db, usuario, reporte_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
