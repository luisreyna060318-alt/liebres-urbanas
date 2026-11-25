"""Esquemas de ubicación (CONTRATO_API, sección 5)."""

from pydantic import BaseModel, Field


class GeoResultado(BaseModel):
    """Un lugar encontrado por Nominatim, ya traducido a los datos que pide el formulario de reporte."""

    etiqueta: str = Field(examples=["Avenida Tecnológico, Partido Escobedo, Ciudad Juárez, Chihuahua, México"])
    lat: float = Field(examples=[31.7001])
    lon: float = Field(examples=[-106.4302])
    calle: str | None = Field(examples=["Avenida Tecnológico"], description="null si Nominatim no trae la calle")
    colonia_id: int | None = Field(
        examples=[12], description="null si el nombre devuelto no coincide con el catálogo: la persona la elige"
    )
    colonia_nombre: str | None = Field(examples=["Partido Escobedo"], description="Nombre según nuestro catálogo")
    dentro_del_municipio: bool = Field(description="RN-01: false si el punto queda fuera de Juárez")


class GeoBusqueda(BaseModel):
    """Respuesta de /api/geo/buscar. Lista vacía si no hubo coincidencias (no es un error)."""

    resultados: list[GeoResultado]
