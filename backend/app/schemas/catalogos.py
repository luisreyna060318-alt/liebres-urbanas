"""Esquemas de salida de los catálogos (CONTRATO_API, sección 4)."""

from pydantic import BaseModel, ConfigDict, Field


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
