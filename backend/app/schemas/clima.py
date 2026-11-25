"""Esquema del aviso de lluvia (CONTRATO_API, sección 13)."""

from datetime import datetime

from pydantic import BaseModel, Field


class AvisoLluvia(BaseModel):
    """Resultado de GET /api/clima/aviso. Si el pronóstico no está disponible, `disponible` es false (HTTP 200)."""

    disponible: bool = Field(description="false si Open-Meteo falló, tardó más de 5 s o respondió algo inválido")
    hay_aviso: bool = Field(description="true si la probabilidad máxima de las próximas 12 h alcanza el umbral")
    probabilidad_max_pct: int | None = Field(
        examples=[45], description="Máxima de las próximas 12 h; null si no hay datos"
    )
    horas: int = Field(examples=[12], description="Horas de pronóstico que se revisan (HORAS_PRONOSTICO)")
    umbral_pct: int = Field(examples=[30], description="Umbral del aviso (UMBRAL_LLUVIA_PCT)")
    consultado_en: datetime | None = Field(description="UTC; cuándo se consultó Open-Meteo. null si no hay datos")
