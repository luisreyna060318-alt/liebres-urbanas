"""Dependencias de FastAPI: sesión de base de datos y protección de rutas.

Uso en una ruta:
    def mi_ruta(usuario: UsuarioActual): ...                         -> exige sesión (401 si no hay)
    def mi_ruta(usuario: Annotated[Usuario, Depends(require_role("moderador", "coordinador"))]): ...
                                                                     -> exige además uno de esos roles (403)
La autorización se verifica SIEMPRE aquí, en el servidor: ocultar un botón en React no protege nada (OWASP A01).
"""

from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errores import ErrorApi
from app.core.security import leer_token
from app.models import Usuario

# auto_error=False: si falta el encabezado, respondemos nosotros con el formato de la API (401 NO_AUTENTICADO).
# HTTPBearer hace que el botón "Authorize" de /docs pida el token que devuelve /api/auth/login.
esquema_bearer = HTTPBearer(auto_error=False, description="Token que devuelve /api/auth/login")

SesionDB = Annotated[Session, Depends(get_db)]


def _no_autenticado() -> ErrorApi:
    return ErrorApi(401, "NO_AUTENTICADO", "Tu sesión no es válida o ya venció. Inicia sesión de nuevo")


def usuario_actual(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(esquema_bearer)], db: SesionDB
) -> Usuario:
    """Devuelve la persona dueña del token, leída SIEMPRE de la base de datos.

    Así un cambio de rol o una suspensión surten efecto en la siguiente petición, sin esperar a que el
    token venza (HU-06.2 CA2). populate_existing obliga a releer la fila aunque la sesión ya la tenga.
    """
    if credenciales is None:
        raise _no_autenticado()
    try:
        usuario_id = leer_token(credenciales.credentials)
    except (jwt.PyJWTError, ValueError):
        raise _no_autenticado() from None
    usuario = db.get(Usuario, usuario_id, populate_existing=True)
    if usuario is None:
        raise _no_autenticado()
    if not usuario.activo:
        raise ErrorApi(403, "CUENTA_SUSPENDIDA", "Tu cuenta está suspendida. Escribe a la asociación para aclararlo")
    return usuario


UsuarioActual = Annotated[Usuario, Depends(usuario_actual)]


def usuario_opcional(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(esquema_bearer)], db: SesionDB
) -> Usuario | None:
    """Para rutas PÚBLICAS que muestran algo más a ciertos roles (por ejemplo, los rechazados a moderación).

    Nunca responde 401: sin token, con un token vencido o inválido, o con la cuenta suspendida, la petición
    se trata como de una persona sin sesión (devuelve None).
    """
    if credenciales is None:
        return None
    try:
        usuario_id = leer_token(credenciales.credentials)
    except (jwt.PyJWTError, ValueError):
        return None
    usuario = db.get(Usuario, usuario_id, populate_existing=True)
    if usuario is None or not usuario.activo:
        return None
    return usuario


UsuarioOpcional = Annotated[Usuario | None, Depends(usuario_opcional)]


def require_role(*roles: str):
    """Crea una dependencia que solo deja pasar a quien tenga alguno de esos roles (403 SIN_PERMISO si no).

    Ejemplo: Annotated[Usuario, Depends(require_role("ciudadano"))]
    """

    def comprobar_rol(usuario: UsuarioActual) -> Usuario:
        if usuario.rol not in roles:
            raise ErrorApi(403, "SIN_PERMISO", "Tu rol no permite realizar esta acción")
        return usuario

    return comprobar_rol
