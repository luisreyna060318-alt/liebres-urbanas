"""Catálogos públicos para llenar formularios y filtros."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import SesionDB
from app.core.reglas import PAGINA_MAX, TAM_PAGINA_CATALOGOS, TAM_PAGINA_MAX_COLONIAS
from app.schemas.catalogos import ColoniaSalida, MotivoRechazoSalida, SectorSalida, TipoDanoSalida
from app.schemas.comun import IdEntero, Pagina, respuestas_error
from app.services import catalogos as catalogos_service

router = APIRouter(prefix="/api", tags=["Catálogos"])


@router.get("/sectores", response_model=list[SectorSalida], summary="Sectores")
def listar_sectores(db: SesionDB):
    """Todos los sectores (agrupaciones de colonias de la asociación), en orden alfabético."""
    return catalogos_service.listar_sectores(db)


@router.get(
    "/colonias", response_model=Pagina[ColoniaSalida], summary="Colonias", responses=respuestas_error(422)
)
def listar_colonias(
    db: SesionDB,
    q: str | None = Query(None, max_length=100, description="Parte del nombre, sin distinguir mayúsculas"),
    sector_id: Annotated[IdEntero | None, Query(description="Solo las de este sector")] = None,
    solo_activas: bool = Query(True, description="false incluye las desactivadas (administración)"),
    pagina: int = Query(1, ge=1, le=PAGINA_MAX, description="Página, empieza en 1"),
    tam: int = Query(
        TAM_PAGINA_CATALOGOS,
        ge=1,
        le=TAM_PAGINA_MAX_COLONIAS,
        description=f"Elementos por página (hasta {TAM_PAGINA_MAX_COLONIAS} para llenar listas desplegables)",
    ),
):
    """Colonias del catálogo oficial con su sector, en orden alfabético y paginadas.

    Ejemplo para llenar el selector de un formulario: `/api/colonias?tam=500`."""
    return catalogos_service.listar_colonias(db, q, sector_id, solo_activas, pagina, tam)


@router.get("/tipos-dano", response_model=list[TipoDanoSalida], summary="Tipos de daño")
def listar_tipos_dano(db: SesionDB):
    """Tipos de daño activos de un bache: bache, hundimiento, grieta y alcantarilla sin tapa."""
    return catalogos_service.listar_tipos_dano(db)


@router.get("/motivos-rechazo", response_model=list[MotivoRechazoSalida], summary="Motivos de rechazo")
def listar_motivos_rechazo(db: SesionDB):
    """Motivos activos con los que un moderador rechaza un reporte. Si `pide_explicacion` es `true`
    (por ejemplo "Otro"), el moderador debe escribir el porqué."""
    return catalogos_service.listar_motivos_rechazo(db)
