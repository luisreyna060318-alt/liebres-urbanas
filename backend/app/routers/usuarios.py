"""Administración de usuarios y roles (HU-06.2). Solo el coordinador."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import SesionDB, require_role
from app.core.reglas import PAGINA_MAX, TAM_PAGINA_CATALOGOS, TAM_PAGINA_MAX
from app.schemas.comun import Pagina, respuestas_error
from app.schemas.usuarios import CambioRolEntrada, Rol, SuspensionEntrada, UsuarioAdmin
from app.services import usuarios as usuarios_service

# Todas las rutas de este archivo exigen rol coordinador (401 sin sesión, 403 con otro rol)
router = APIRouter(
    prefix="/api/usuarios",
    tags=["Administración de usuarios"],
    dependencies=[Depends(require_role("coordinador"))],
)


@router.get(
    "", response_model=Pagina[UsuarioAdmin], summary="Listar usuarios", responses=respuestas_error(401, 403, 422)
)
def listar_usuarios(
    db: SesionDB,
    q: str | None = Query(None, max_length=100, description="Parte del nombre o del correo, sin distinguir mayúsculas"),
    rol: Annotated[Rol | None, Query(description="Solo las cuentas con este rol")] = None,
    pagina: int = Query(1, ge=1, le=PAGINA_MAX, description="Página, empieza en 1"),
    tam: int = Query(TAM_PAGINA_CATALOGOS, ge=1, le=TAM_PAGINA_MAX, description="Elementos por página"),
):
    """Cuentas en orden alfabético, 10 por página. Nunca incluye la contraseña ni su hash."""
    return usuarios_service.listar_usuarios(db, q, rol, pagina, tam)


@router.put(
    "/{usuario_id}/rol",
    response_model=UsuarioAdmin,
    summary="Cambiar el rol",
    responses=respuestas_error(401, 403, 404, 409, 422),
)
def cambiar_rol(usuario_id: int, datos: CambioRolEntrada, db: SesionDB):
    """Cambia el rol (`ciudadano`, `moderador` o `coordinador`). Surte efecto en la siguiente petición de esa persona.
    No se puede quitar el rol al último coordinador activo (409 `ULTIMO_COORDINADOR`)."""
    return usuarios_service.cambiar_rol(db, usuario_id, datos.rol)


@router.put(
    "/{usuario_id}/suspension",
    response_model=UsuarioAdmin,
    summary="Suspender o reactivar",
    responses=respuestas_error(401, 403, 404, 409, 422),
)
def cambiar_suspension(usuario_id: int, datos: SuspensionEntrada, db: SesionDB):
    """`suspendido: true` pone `activo: false`: la persona ya no puede entrar (ni siquiera con un token vigente) y
    sus reportes se conservan. No se puede suspender al último coordinador activo (409 `ULTIMO_COORDINADOR`)."""
    return usuarios_service.cambiar_suspension(db, usuario_id, datos.suspendido)
