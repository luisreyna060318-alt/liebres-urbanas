"""Esquemas de la administración de usuarios (CONTRATO_API, sección 12). Entrada y salida distintas a propósito."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.reglas import ROLES

# Los roles válidos salen de core/reglas.py; Literal hace que Pydantic rechace cualquier otro con 422
Rol = Literal[*ROLES]


class UsuarioAdmin(BaseModel):
    """Lo que ve el coordinador de cada cuenta. NUNCA incluye la contraseña ni su hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(examples=[7])
    nombre: str = Field(examples=["Ana Pérez"])
    correo: str = Field(examples=["ana@ejemplo.test"])
    rol: str = Field(examples=["ciudadano"])
    activo: bool = Field(description="false = cuenta suspendida (no puede entrar y conserva sus reportes)")
    creado_en: datetime


class CambioRolEntrada(BaseModel):
    rol: Rol = Field(examples=["moderador"])


class SuspensionEntrada(BaseModel):
    suspendido: bool = Field(description="true suspende la cuenta; false la reactiva", examples=[True])
