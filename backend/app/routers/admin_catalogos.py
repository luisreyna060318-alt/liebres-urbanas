"""Administración de sectores y colonias (HU-06.1). Solo el coordinador. Las lecturas siguen en catalogos.py."""

from fastapi import APIRouter, Depends, Response

from app.core.deps import SesionDB, require_role
from app.schemas.catalogos import (
    ColoniaActualizacion,
    ColoniaEntrada,
    ColoniaSalida,
    SectorEntrada,
    SectorSalida,
)
from app.schemas.comun import IdEntero, respuestas_error
from app.services import catalogos as catalogos_service

# Todas las rutas de este archivo exigen rol coordinador (401 sin sesión, 403 con otro rol)
router = APIRouter(
    prefix="/api",
    tags=["Administración de catálogos"],
    dependencies=[Depends(require_role("coordinador"))],
)


@router.post(
    "/sectores",
    response_model=SectorSalida,
    status_code=201,
    summary="Crear sector",
    responses=respuestas_error(401, 403, 409, 422),
)
def crear_sector(datos: SectorEntrada, db: SesionDB):
    """Crea un sector. El nombre es único (409 `SECTOR_DUPLICADO`)."""
    return catalogos_service.crear_sector(db, datos)


@router.put(
    "/sectores/{sector_id}",
    response_model=SectorSalida,
    summary="Renombrar sector",
    responses=respuestas_error(401, 403, 404, 409, 422),
)
def actualizar_sector(sector_id: IdEntero, datos: SectorEntrada, db: SesionDB):
    return catalogos_service.actualizar_sector(db, sector_id, datos)


@router.post(
    "/colonias",
    response_model=ColoniaSalida,
    status_code=201,
    summary="Crear colonia",
    responses=respuestas_error(401, 403, 409, 422),
)
def crear_colonia(datos: ColoniaEntrada, db: SesionDB):
    """Crea una colonia activa. El nombre es único dentro de su sector (409 `COLONIA_DUPLICADA`)."""
    return catalogos_service.crear_colonia(db, datos)


@router.put(
    "/colonias/{colonia_id}",
    response_model=ColoniaSalida,
    summary="Editar o desactivar colonia",
    responses=respuestas_error(401, 403, 404, 409, 422),
)
def actualizar_colonia(colonia_id: IdEntero, datos: ColoniaActualizacion, db: SesionDB):
    """Reemplaza los datos de la colonia; `activa: false` la desactiva (deja de ofrecerse en los formularios)."""
    return catalogos_service.actualizar_colonia(db, colonia_id, datos)


@router.delete(
    "/colonias/{colonia_id}",
    status_code=204,
    summary="Eliminar colonia",
    responses=respuestas_error(401, 403, 404, 409),
)
def borrar_colonia(colonia_id: IdEntero, db: SesionDB):
    """Elimina una colonia sin reportes. Con reportes responde 409 `COLONIA_CON_REPORTES`: solo se puede desactivar."""
    catalogos_service.borrar_colonia(db, colonia_id)
    return Response(status_code=204)
