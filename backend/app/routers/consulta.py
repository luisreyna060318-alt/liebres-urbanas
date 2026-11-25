"""Consulta pública de reportes (HU-04.1 y HU-04.2) y su detalle (HU-04.4).

Sin lógica: recibe los filtros, llama al servicio y responde.

Es pública: no exige sesión. Si llega un token válido de moderador o coordinador, el servicio además deja
consultar los rechazados con estado=rechazado; un token vencido o inválido se trata como público (no da 401).
"""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.core.deps import SesionDB, UsuarioOpcional
from app.core.reglas import (
    CATEGORIAS,
    ESTADOS_BACHE,
    ESTADOS_ENCHARCAMIENTO,
    PAGINA_MAX,
    SEVERIDADES,
    TAM_PAGINA_CONSULTA,
    TAM_PAGINA_MAX,
)
from app.schemas.comun import Pagina, respuestas_error
from app.schemas.reportes import ReporteDetalle, ReportePublico
from app.services import consulta as consulta_service

router = APIRouter(prefix="/api", tags=["Consulta pública"])

# Estados de las dos categorías, sin repetir "rechazado"
ESTADOS = tuple(dict.fromkeys(ESTADOS_BACHE + ESTADOS_ENCHARCAMIENTO))
Q_MAX = 100


@router.get(
    "/reportes",
    response_model=Pagina[ReportePublico],
    summary="Consultar reportes",
    responses=respuestas_error(422),
)
def consultar_reportes(
    db: SesionDB,
    usuario: UsuarioOpcional,
    categoria: Literal[CATEGORIAS] | None = Query(None, description="bache o encharcamiento"),
    estado: Literal[ESTADOS] | None = Query(None, description="Sin valor: solo los activos"),
    colonia_id: int | None = Query(None, ge=1),
    severidad: Literal[SEVERIDADES] | None = Query(None, description="Solo baches"),
    desde: Annotated[date | None, Query(description="AAAA-MM-DD, día de Ciudad Juárez (incluido)")] = None,
    hasta: Annotated[date | None, Query(description="AAAA-MM-DD, día de Ciudad Juárez (incluido)")] = None,
    q: str | None = Query(None, max_length=Q_MAX, description="Parte de la calle o del folio"),
    pagina: int = Query(1, ge=1, le=PAGINA_MAX, description="Empieza en 1"),
    tam: int = Query(TAM_PAGINA_CONSULTA, ge=1, le=TAM_PAGINA_MAX),
):
    """Reportes del más reciente al más antiguo, **20 por página** con el total. Nunca incluye al autor.

    - Sin `estado`: solo los **activos** (baches en recibido, validado o en reparación y encharcamientos activos).
    - Con `estado` se consultan también reparados e históricos. Los **rechazados** nunca se muestran al público;
      un moderador o coordinador con sesión los ve con `estado=rechazado`.
    - `q` busca en la calle o el folio sin distinguir mayúsculas. `desde` > `hasta` → 422 `VALIDACION`."""
    filtro = consulta_service.FiltroReportes(
        categoria=categoria,
        estados=(estado,) if estado else None,
        colonia_id=colonia_id,
        severidad=severidad,
        desde=desde,
        hasta=hasta,
        q=q,
    )
    return consulta_service.listar_publicos(db, usuario, filtro, pagina, tam)


# ":int" hace que solo un número entre a esta ruta: /reportes/cercanos o /reportes/baches nunca se confunden con un id
@router.get(
    "/reportes/{reporte_id:int}",
    response_model=ReporteDetalle,
    summary="Detalle e historial de un reporte",
    responses=respuestas_error(404),
)
def detalle_reporte(reporte_id: int, db: SesionDB, usuario: UsuarioOpcional):
    """Datos del reporte, confirmaciones, estado e **historial público** del más reciente al más antiguo (sin quién
    hizo cada cambio). Incluye `longevidad_dias` y `ultima_confirmacion`.

    404 `NO_ENCONTRADO` si no existe o si está rechazado y no tienes sesión de moderador o coordinador."""
    return consulta_service.obtener_detalle(db, usuario, reporte_id)
