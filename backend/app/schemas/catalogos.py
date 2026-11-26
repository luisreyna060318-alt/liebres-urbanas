"""Esquemas de salida de los catálogos (CONTRATO_API, sección 4)."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.reglas import NOMBRE_COLONIA_MAX, NOMBRE_COLONIA_MIN, NOMBRE_SECTOR_MAX
from app.schemas.comun import IdEntero


class SectorSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(examples=[1])
    nombre: str = Field(examples=["Centro"])


class ColoniaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(examples=[12])
    nombre: str = Field(examples=["Partido Escobedo"])
    sector: SectorSalida
    activa: bool
    lat: float | None = Field(examples=[31.7302])
    lon: float | None = Field(examples=[-106.4801])


class TipoDanoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str = Field(examples=["alcantarilla_sin_tapa"])
    nombre: str = Field(examples=["Alcantarilla sin tapa"])


class MotivoRechazoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str = Field(examples=["otro"])
    nombre: str = Field(examples=["Otro"])
    pide_explicacion: bool = Field(description="Si es true, el moderador debe escribir una explicación")


# --- Entradas de administración (HU-06.1, CONTRATO_API sección 11). Distintas de las de salida a propósito ---
def _limpiar_nombre(v: str, minimo: int, maximo: int) -> str:
    v = " ".join(v.split())  # quita espacios de sobra
    if not minimo <= len(v) <= maximo:
        raise ValueError(f"El nombre debe tener entre {minimo} y {maximo} caracteres")
    return v


class SectorEntrada(BaseModel):
    """Crear o renombrar un sector."""

    nombre: str = Field(examples=["Centro"], description=f"Hasta {NOMBRE_SECTOR_MAX} caracteres; único")

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        return _limpiar_nombre(v, NOMBRE_COLONIA_MIN, NOMBRE_SECTOR_MAX)


class ColoniaEntrada(BaseModel):
    """Alta de colonia. Las coordenadas (centro aproximado) son opcionales, pero van las dos o ninguna."""

    nombre: str = Field(examples=["Colonia Ficticia"], description=f"Hasta {NOMBRE_COLONIA_MAX} caracteres")
    sector_id: IdEntero = Field(examples=[1])
    lat: float | None = Field(default=None, ge=-90, le=90, examples=[31.73])
    lon: float | None = Field(default=None, ge=-180, le=180, examples=[-106.48])

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        return _limpiar_nombre(v, NOMBRE_COLONIA_MIN, NOMBRE_COLONIA_MAX)


class ColoniaActualizacion(ColoniaEntrada):
    """Edición de colonia (PUT, se envía todo): agrega `activa` para desactivarla o reactivarla."""

    activa: bool
