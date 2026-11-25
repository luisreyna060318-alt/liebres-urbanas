"""Rutas de cuenta y sesión. Sin lógica: reciben, llaman al servicio y responden."""

from fastapi import APIRouter, status

from app.core.deps import SesionDB, UsuarioActual
from app.schemas.auth import LoginEntrada, RegistroEntrada, SesionRespuesta, UsuarioPublico
from app.schemas.comun import respuestas_error
from app.services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["Cuenta y sesión"])


@router.post(
    "/registro",
    response_model=SesionRespuesta,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una cuenta",
    responses={409: {"description": "`CORREO_REGISTRADO`: el correo ya tiene cuenta"}, **respuestas_error(422)},
)
def registrar(datos: RegistroEntrada, db: SesionDB):
    """Crea una cuenta con rol **ciudadano** y deja a la persona dentro (devuelve su token).

    - `nombre`: de 2 a 80 caracteres.
    - `correo`: válido; no distingue mayúsculas (Ana@x.test y ana@x.test son la misma cuenta).
    - `password`: 8 caracteres o más, con letras y números.
    - `acepta_privacidad`: debe ser `true`.

    Cada error de campo llega en `campos` con el nombre del campo (HU-01.1 CA3)."""
    usuario = auth_service.registrar(db, datos)
    return auth_service.sesion_para(usuario)


@router.post(
    "/login",
    response_model=SesionRespuesta,
    summary="Iniciar sesión",
    responses={
        401: {"description": "`CREDENCIALES`: correo o contraseña incorrectos (mismo mensaje para ambos)"},
        403: {"description": "`CUENTA_SUSPENDIDA`"},
    },
)
def iniciar_sesion(datos: LoginEntrada, db: SesionDB):
    """Devuelve un token JWT de **30 minutos**. Se manda después como `Authorization: Bearer <token>`.

    Para probar en esta página: copia `access_token` y pégalo en el botón **Authorize**."""
    usuario = auth_service.autenticar(db, datos.correo, datos.password)
    return auth_service.sesion_para(usuario)


@router.post(
    "/refresh",
    response_model=SesionRespuesta,
    summary="Renovar el token",
    responses=respuestas_error(401, 403),
)
def renovar(usuario: UsuarioActual):
    """Con un token **todavía vigente**, devuelve uno nuevo de 30 minutos.

    El frontend lo llama mientras hay actividad; si pasan 30 minutos sin actividad el token vence y hay que
    iniciar sesión otra vez (HU-01.2 CA4). Una cuenta suspendida no puede renovar."""
    return auth_service.sesion_para(usuario)


@router.get(
    "/yo",
    response_model=UsuarioPublico,
    summary="¿Quién soy?",
    responses=respuestas_error(401, 403),
)
def quien_soy(usuario: UsuarioActual):
    """Datos de la persona dueña del token, leídos de la base en este momento (el rol puede haber cambiado)."""
    return usuario
