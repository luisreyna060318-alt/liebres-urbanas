"""Cálculos geográficos sencillos (duplicados a 30/50 m, "¿Cómo está mi zona?" a 1 km).

No se usa PostGIS para que todo funcione igual en PostgreSQL y en SQLite. La forma de buscar cercanos es:
1. Prefiltrar en SQL con una "caja" (rectángulo de lat/lon) alrededor del punto; usa el índice (lat, lon).
2. Calcular la distancia real con Haversine en Python solo para esos pocos candidatos y quedarse con los
   que están dentro del radio.
"""

import math

RADIO_TIERRA_M = 6_371_000  # radio medio de la Tierra
METROS_POR_GRADO_LAT = 111_320  # aproximado; se usa solo para la caja (que es un poco más grande de lo necesario)


def distancia_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en metros entre dos puntos (fórmula de Haversine)."""
    fi1, fi2 = math.radians(lat1), math.radians(lat2)
    delta_fi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_fi / 2) ** 2 + math.cos(fi1) * math.cos(fi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * RADIO_TIERRA_M * math.asin(math.sqrt(a))


def caja(lat: float, lon: float, radio_m: float) -> tuple[float, float, float, float]:
    """Rectángulo (lat_min, lat_max, lon_min, lon_max) que contiene el círculo de ese radio.

    Uso en una consulta:
        lat_min, lat_max, lon_min, lon_max = caja(lat, lon, 30)
        select(Reporte).where(Reporte.lat.between(lat_min, lat_max), Reporte.lon.between(lon_min, lon_max))
    y después se filtra con distancia_m(). Se agrega un 10 % de margen para no perder puntos en las orillas.
    """
    margen = radio_m * 1.1
    delta_lat = margen / METROS_POR_GRADO_LAT
    # Un grado de longitud mide menos conforme nos alejamos del ecuador (cos de la latitud)
    delta_lon = margen / (METROS_POR_GRADO_LAT * max(math.cos(math.radians(lat)), 0.01))
    return lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon
