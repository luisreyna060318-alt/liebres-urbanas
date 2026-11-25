"""Esquemas de salida del tablero de indicadores (HU-07.1, CONTRATO_API sección 14).

PRIVACIDAD (RN-04): solo cifras, folios, calles y colonias. Nada del autor ni de quién hizo cada cambio.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.core.reglas import CATEGORIAS
from app.schemas.reportes import ColoniaCorta


class FiltroAplicado(BaseModel):
    desde: date | None
    hasta: date | None
    sector_id: int | None


class TotalEstado(BaseModel):
    categoria: Literal[CATEGORIAS]
    estado: str = Field(examples=["validado"])
    total: int


class Totales(BaseModel):
    total: int = Field(description="Todos los reportes del filtro, sin los rechazados")
    bache: int
    encharcamiento: int
    por_estado: list[TotalEstado] = Field(description="Cada estado de cada categoría (sin rechazado), incluso en 0")
    rechazados: int = Field(description="Rechazados del filtro (las dos categorías); no suman en `total`")


class ColoniaAbiertos(BaseModel):
    colonia: ColoniaCorta
    abiertos: int = Field(description="Baches en recibido, validado o en reparación")


class Semana(BaseModel):
    inicio: date = Field(description="Lunes en que empieza la semana (hora de Juárez)")
    total: int


class BacheLongevo(BaseModel):
    id: int
    folio: str = Field(examples=["BCH-2026-000123"])
    calle: str
    colonia: ColoniaCorta
    estado: str
    antiguedad_dias: int = Field(description="Días desde creado_en hasta hoy (RN-10)")


class LongevidadColonia(BaseModel):
    colonia: ColoniaCorta
    abiertos: int
    promedio_dias: float = Field(description="Antigüedad promedio de sus baches abiertos, con un decimal")


class TableroSalida(BaseModel):
    filtro: FiltroAplicado
    totales: Totales
    top_colonias: list[ColoniaAbiertos]
    tiempo_promedio_reparacion_dias: float | None = Field(
        description="Promedio de días de Validado a Reparado según el historial; null si no hay datos"
    )
    reparados_medidos: int = Field(description="Cuántos baches reparados entran en ese promedio")
    por_semana: list[Semana] = Field(description="12 semanas, de la más antigua a la más reciente")
    mas_longevos: list[BacheLongevo]
    longevidad_por_colonia: list[LongevidadColonia]
