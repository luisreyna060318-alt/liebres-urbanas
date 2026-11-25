"""Esquema de salida de "¿Cómo está mi zona?" (CONTRATO_API, sección 9). Sin datos del autor (RN-04):
los reportes son `Cercano` (ReportePublico + distancia_m)."""

from pydantic import BaseModel, Field

from app.schemas.reportes import Cercano


class PuntoZona(BaseModel):
    lat: float = Field(examples=[31.7001])
    lon: float = Field(examples=[-106.4302])


class ZonaRespuesta(BaseModel):
    centro: PuntoZona = Field(description="El punto consultado, tal como se recibió")
    radio_m: int = Field(examples=[1000], description="Radio de búsqueda en metros (RADIO_ZONA_KM)")
    total: int = Field(description="Reportes activos en el radio, aunque `items` esté recortado por el tope")
    items: list[Cercano] = Field(description="Intransitables primero y luego por distancia; hasta MAX_RESULTADOS_ZONA")
