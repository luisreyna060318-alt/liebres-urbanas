"""Reportes cercanos a un punto: duplicados de baches (30 m) y de encharcamientos (50 m) (HU-02.3, HU-03.1 CA4).

Dos pasos (ver core/geo.py): una "caja" en SQL que usa el índice (lat, lon) y después la distancia real con
Haversine solo para esos pocos candidatos.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.errores import ErrorApi
from app.core.geo import caja, distancia_m
from app.core.reglas import RADIO_DUPLICADO_BACHE_M, RADIO_DUPLICADO_ENCHARCAMIENTO_M
from app.core.tiempo import a_hora_local, ahora_utc
from app.models import Reporte
from app.schemas.reportes import ESTADOS_BACHE_ABIERTOS, Cercano, a_cercano

RADIOS_M = {"bache": RADIO_DUPLICADO_BACHE_M, "encharcamiento": RADIO_DUPLICADO_ENCHARCAMIENTO_M}


def buscar_cercanos(
    db: Session, categoria: str, lat: float, lon: float, ahora: datetime | None = None
) -> list[tuple[Reporte, float]]:
    """Pares (reporte, distancia en metros) dentro del radio de la categoría, del más cercano al más lejano.

    - Baches: solo abiertos (recibido, validado, en_reparacion).
    - Encharcamientos: solo activos y todavía vigentes (vigente_hasta en el futuro).
    """
    ahora = ahora or ahora_utc()
    radio = RADIOS_M[categoria]
    lat_min, lat_max, lon_min, lon_max = caja(lat, lon, radio)
    consulta = (
        select(Reporte)
        .options(joinedload(Reporte.tipo_dano), joinedload(Reporte.colonia))
        .where(
            Reporte.categoria == categoria,
            Reporte.lat.between(lat_min, lat_max),
            Reporte.lon.between(lon_min, lon_max),
        )
    )
    if categoria == "bache":
        consulta = consulta.where(Reporte.estado.in_(ESTADOS_BACHE_ABIERTOS))
    else:
        consulta = consulta.where(Reporte.estado == "activo", Reporte.vigente_hasta > ahora)

    pares = [(r, distancia_m(lat, lon, r.lat, r.lon)) for r in db.scalars(consulta)]
    dentro = [(r, d) for r, d in pares if d <= radio]
    return sorted(dentro, key=lambda par: par[1])


def cercanos_publicos(
    db: Session, categoria: str, lat: float, lon: float, ahora: datetime | None = None
) -> list[Cercano]:
    """Lo mismo que buscar_cercanos, ya convertido al esquema Cercano (ReportePublico + distancia_m)."""
    ahora = ahora or ahora_utc()
    hoy = a_hora_local(ahora).date()
    return [a_cercano(r, hoy, d) for r, d in buscar_cercanos(db, categoria, lat, lon, ahora)]


def rechazar_si_hay_duplicados(db: Session, categoria: str, lat: float, lon: float, ahora: datetime) -> None:
    """HU-02.3: 409 POSIBLE_DUPLICADO con la lista `duplicados` si hay un reporte abierto cerca.

    La persona puede confirmar uno de ellos o volver a enviar con `forzar: true` (CA4: reportar de todos modos).
    """
    duplicados = cercanos_publicos(db, categoria, lat, lon, ahora)
    if duplicados:
        raise ErrorApi(
            409,
            "POSIBLE_DUPLICADO",
            "Ya hay un reporte muy cerca de este punto. Confírmalo o repórtalo de todos modos",
            extra={"duplicados": [d.model_dump(mode="json") for d in duplicados]},
        )
