"""Catálogos: sectores, colonias, tipos de daño y motivos de rechazo."""

from sqlalchemy import Boolean, Float, ForeignKey, String, UniqueConstraint, false, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Sector(Base):
    """Agrupación de colonias que usa la asociación (no es oficial)."""

    __tablename__ = "sectores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)

    colonias: Mapped[list["Colonia"]] = relationship(back_populates="sector")


class Colonia(Base):
    """Colonia del catálogo oficial (SEPOMEX/INEGI). Con reportes no se borra: se desactiva (HU-06.1 CA2)."""

    __tablename__ = "colonias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    sector_id: Mapped[int] = mapped_column(ForeignKey("sectores.id"), index=True)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    lat: Mapped[float | None] = mapped_column(Float)  # punto aproximado (centro) de la colonia
    lon: Mapped[float | None] = mapped_column(Float)
    fuente: Mapped[str | None] = mapped_column(String(200))  # de dónde salió el dato (RNF-09)

    sector: Mapped[Sector] = relationship(back_populates="colonias")

    # El mismo nombre puede repetirse en sectores distintos, pero no dentro del mismo (HU-06.1 CA3)
    __table_args__ = (UniqueConstraint("sector_id", "nombre"),)


class TipoDano(Base):
    """Tipo de daño de un bache: bache, hundimiento, grieta, alcantarilla_sin_tapa."""

    __tablename__ = "tipos_dano"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True)  # valor estable que usa el código
    nombre: Mapped[str] = mapped_column(String(80))  # etiqueta para mostrar
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class MotivoRechazo(Base):
    """Motivo con el que un moderador rechaza un reporte. Si pide_explicacion, el texto es obligatorio."""

    __tablename__ = "motivos_rechazo"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True)
    nombre: Mapped[str] = mapped_column(String(80))
    pide_explicacion: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
