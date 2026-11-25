"""Esquemas de cuenta y sesión (CONTRATO_API, sección 3).

Entrada y salida son esquemas distintos a propósito: la salida (UsuarioPublico) nunca incluye password_hash.
"""

import re
from typing import Literal

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.reglas import INACTIVIDAD_MIN, NOMBRE_MAX, NOMBRE_MIN, PASSWORD_MIN
from app.core.security import MAX_BYTES_PASSWORD
from app.models import normalizar_correo

CORREO_MAX = 120


class RegistroEntrada(BaseModel):
    """Datos para crear una cuenta (HU-01.1). El rol NO se pide: siempre nace como ciudadano."""

    nombre: str = Field(examples=["Ana Pérez"], description=f"De {NOMBRE_MIN} a {NOMBRE_MAX} caracteres")
    correo: str = Field(examples=["ana@ejemplo.test"])
    password: str = Field(examples=["Clave1234"], description=f"{PASSWORD_MIN} caracteres o más, con letras y números")
    acepta_privacidad: bool = Field(
        default=False, validate_default=True, description="Debe ser true: aceptación del aviso de privacidad"
    )

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = " ".join(v.split())  # quita espacios de sobra
        if not NOMBRE_MIN <= len(v) <= NOMBRE_MAX:
            raise ValueError(f"El nombre debe tener entre {NOMBRE_MIN} y {NOMBRE_MAX} caracteres")
        return v

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, v: str) -> str:
        v = normalizar_correo(v)
        if len(v) > CORREO_MAX:
            raise ValueError(f"El correo no puede pasar de {CORREO_MAX} caracteres")
        try:
            # test_environment=True acepta dominios .test (los de las cuentas de ejemplo) y no consulta DNS
            validate_email(v, check_deliverability=False, test_environment=True)
        except EmailNotValidError:
            raise ValueError("Escribe un correo electrónico válido, por ejemplo ana@ejemplo.test") from None
        return v

    @field_validator("password")
    @classmethod
    def validar_password(cls, v: str) -> str:
        if len(v) < PASSWORD_MIN or not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", v) or not re.search(r"\d", v):
            raise ValueError(f"La contraseña debe tener al menos {PASSWORD_MIN} caracteres, con letras y números")
        if len(v.encode("utf-8")) > MAX_BYTES_PASSWORD:
            raise ValueError("La contraseña es demasiado larga")
        return v

    @field_validator("acepta_privacidad")
    @classmethod
    def validar_privacidad(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("Debes aceptar el aviso de privacidad para crear tu cuenta")
        return v


class LoginEntrada(BaseModel):
    """Correo y contraseña. Aquí no se valida el formato: cualquier fallo responde el mismo 401."""

    correo: str = Field(min_length=1, max_length=200, examples=["ciudadano@liebreurbana.test"])
    password: str = Field(min_length=1, max_length=200, examples=["Clave1234"])


class UsuarioPublico(BaseModel):
    """Datos de la cuenta que se devuelven a la propia persona (o al coordinador). Nunca el hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(examples=[7])
    nombre: str = Field(examples=["Ana Pérez"])
    correo: str = Field(examples=["ana@ejemplo.test"])
    rol: str = Field(examples=["ciudadano"])


class SesionRespuesta(BaseModel):
    """Lo que devuelven registro, login y refresh: el token y quién es la persona."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expira_en_min: int = Field(default=INACTIVIDAD_MIN, examples=[INACTIVIDAD_MIN])
    usuario: UsuarioPublico
