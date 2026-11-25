"""Cuentas de usuario y sus colonias de interés."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, func, true
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.core.database import Base
from app.core.reglas import ROL_INICIAL, ROLES, valores_sql
from app.core.tiempo import FechaHoraUTC, ahora_utc


def normalizar_correo(correo: str) -> str:
    """Ana@Ejemplo.test y ' ana@ejemplo.test ' son la misma cuenta: se guarda sin espacios y en minúsculas."""
    return correo.strip().lower()


class Usuario(Base):
    """Persona con cuenta. Tiene un solo rol (interpretación 2 de DISENO_TECNICO)."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))
    correo: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))  # nunca la contraseña en claro; nunca sale en la API
    rol: Mapped[str] = mapped_column(String(20), default=ROL_INICIAL, server_default=ROL_INICIAL)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())  # False = suspendida
    acepto_privacidad_en: Mapped[datetime | None] = mapped_column(FechaHoraUTC)
    creado_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc, server_default=func.now())

    __table_args__ = (CheckConstraint(f"rol IN {valores_sql(ROLES)}", name="rol_valido"),)

    @validates("correo")
    def _normalizar_correo(self, _llave: str, correo: str) -> str:
        return normalizar_correo(correo)


# Correo único sin distinguir mayúsculas (HU-01.1 CA2): índice único sobre lower(correo).
# Va fuera de la clase porque necesita la columna ya creada. Además el modelo normaliza el correo al guardarlo.
Index("uq_usuarios_correo_lower", func.lower(Usuario.correo), unique=True)


class UsuarioColonia(Base):
    """Colonias de interés de una persona (relación N:M, HU-01.4, P1)."""

    __tablename__ = "usuario_colonias"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    colonia_id: Mapped[int] = mapped_column(ForeignKey("colonias.id", ondelete="CASCADE"), primary_key=True)
