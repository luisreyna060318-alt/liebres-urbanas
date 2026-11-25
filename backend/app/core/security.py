"""Seguridad: hash de contraseñas (bcrypt) y tokens de sesión (JWT con PyJWT).

Sesión sin estado: al iniciar sesión el servidor firma un JWT con su SECRET_KEY y el cliente lo manda en cada
petición. El token dura INACTIVIDAD_MIN (30 min) y el frontend lo renueva con /auth/refresh mientras la persona
está activa; si pasa media hora sin actividad, vence y hay que entrar de nuevo (HU-01.2 CA4).
El token solo lleva el id: el rol y el estado de la cuenta se leen de la base en cada petición (deps.py).
"""

from datetime import timedelta

import bcrypt
import jwt

from app.core.config import settings
from app.core.reglas import INACTIVIDAD_MIN
from app.core.tiempo import ahora_utc

# bcrypt solo procesa los primeros 72 BYTES (no caracteres: una "é" ocupa 2) y desde la versión 5
# lanza ValueError si se pasa de ahí. Los esquemas de entrada ya lo validan.
MAX_BYTES_PASSWORD = 72


def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de la contraseña (con sal aleatoria). La contraseña nunca se guarda."""
    datos = password.encode("utf-8")
    if len(datos) > MAX_BYTES_PASSWORD:
        raise ValueError(f"La contraseña no puede pasar de {MAX_BYTES_PASSWORD} bytes")
    return bcrypt.hashpw(datos, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """True si la contraseña corresponde al hash guardado."""
    datos = password.encode("utf-8")
    if len(datos) > MAX_BYTES_PASSWORD:
        return False  # no pudo haberse guardado una así: es un login fallido, no un error 500
    return bcrypt.checkpw(datos, password_hash.encode("utf-8"))


def crear_token(usuario_id: int, expira_en: timedelta | None = None) -> str:
    """Crea un JWT firmado con el id del usuario ("sub") y su vencimiento ("exp")."""
    ahora = ahora_utc()
    if expira_en is None:
        expira_en = timedelta(minutes=INACTIVIDAD_MIN)
    datos = {"sub": str(usuario_id), "iat": ahora, "exp": ahora + expira_en}
    return jwt.encode(datos, settings.secret_key, algorithm=settings.jwt_algorithm)


def leer_token(token: str) -> int:
    """Verifica la firma y el vencimiento y devuelve el id del usuario.

    Lanza jwt.PyJWTError (o ValueError) si el token está manipulado, vencido o mal formado. Se fija la lista
    de algoritmos aceptados para rechazar trucos como "alg": "none".
    """
    datos = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub"]},
    )
    return int(datos["sub"])
