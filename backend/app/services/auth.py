"""Registro, inicio de sesión y renovación del token (HU-01.1 y HU-01.2)."""

from functools import cache

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errores import ErrorApi
from app.core.reglas import INACTIVIDAD_MIN, ROL_INICIAL
from app.core.security import crear_token, hash_password, verify_password
from app.core.tiempo import ahora_utc
from app.models import Usuario, normalizar_correo
from app.schemas.auth import RegistroEntrada

# Mismo mensaje si falla el correo o la contraseña: así no se puede averiguar qué correos existen (HU-01.2 CA2)
MENSAJE_CREDENCIALES = "Correo o contraseña incorrectos"


def _correo_registrado() -> ErrorApi:
    return ErrorApi(409, "CORREO_REGISTRADO", "Ese correo ya tiene una cuenta. Inicia sesión o usa otro correo")


@cache
def _hash_falso() -> str:
    """Hash de una contraseña inventada. Se compara cuando el correo no existe para que el login tarde lo
    mismo con un correo inexistente que con uno real (si no, el tiempo de respuesta revelaría qué correos hay)."""
    return hash_password("contrasena-inexistente-1")


def buscar_por_correo(db: Session, correo: str) -> Usuario | None:
    """Busca sin distinguir mayúsculas ni espacios."""
    return db.scalar(select(Usuario).where(func.lower(Usuario.correo) == normalizar_correo(correo)))


def registrar(db: Session, datos: RegistroEntrada) -> Usuario:
    """Crea la cuenta. Siempre nace con rol ciudadano (CA1); solo un coordinador puede cambiarlo después.
    El esquema ya exigió la aceptación del aviso de privacidad (CA4); aquí se guarda cuándo se aceptó."""
    if buscar_por_correo(db, datos.correo):
        raise _correo_registrado()
    usuario = Usuario(
        nombre=datos.nombre,
        correo=datos.correo,
        password_hash=hash_password(datos.password),
        rol=ROL_INICIAL,
        acepto_privacidad_en=ahora_utc(),
    )
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        # Dos registros simultáneos con el mismo correo: el índice único de la base lo detecta
        db.rollback()
        raise _correo_registrado() from None
    db.refresh(usuario)
    return usuario


def autenticar(db: Session, correo: str, password: str) -> Usuario:
    """Comprueba correo y contraseña. Una cuenta suspendida no entra (403 CUENTA_SUSPENDIDA)."""
    usuario = buscar_por_correo(db, correo)
    hash_guardado = usuario.password_hash if usuario else _hash_falso()
    contrasena_correcta = verify_password(password, hash_guardado)
    if usuario is None or not contrasena_correcta:
        raise ErrorApi(401, "CREDENCIALES", MENSAJE_CREDENCIALES)
    if not usuario.activo:
        # Solo se llega aquí con la contraseña correcta, así que no le revela nada a un extraño
        raise ErrorApi(403, "CUENTA_SUSPENDIDA", "Tu cuenta está suspendida. Escribe a la asociación para aclararlo")
    return usuario


def sesion_para(usuario: Usuario) -> dict:
    """Arma la SesionRespuesta del contrato con un token nuevo de 30 minutos (también la usa el refresh)."""
    return {
        "access_token": crear_token(usuario.id),
        "token_type": "bearer",
        "expira_en_min": INACTIVIDAD_MIN,
        "usuario": usuario,
    }
