"""¿Cómo está mi zona? (HU-04.3): reportes activos a 1 km o menos de un punto.

Mismo método que los duplicados (core/geo.py): caja en SQL y Haversine en Python para los candidatos.
"""

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.geo import caja, distancia_m
from app.core.reglas import MAX_RESULTADOS_ZONA, RADIO_ZONA_KM
from app.core.tiempo import a_hora_local, ahora_utc
from app.models import Reporte
from app.schemas.reportes import ESTADOS_BACHE_ABIERTOS, a_cercano
from app.schemas.zona import PuntoZona, ZonaRespuesta
from app.services.encharcamientos import expirar_vencidos
from app.services.validaciones import validar_municipio


def consultar_zona(db: Session, lat: float, lon: float) -> ZonaRespuesta:
    """Reportes activos dentro del radio de la zona.

    - Activos: baches abiertos (recibido, validado, en_reparacion) y encharcamientos activos y vigentes.
    - Orden: los encharcamientos «intransitable» primero (son un riesgo) y luego, de cada grupo, el más cercano.
    - `total` cuenta todos; `items` se recorta a MAX_RESULTADOS_ZONA después de ordenar, así los intransitables
      nunca se quedan fuera.
    """
    validar_municipio(lat, lon)  # fuera de Juárez -> 422 FUERA_DEL_MUNICIPIO, igual que el alta
    expirar_vencidos(db)  # pasa a histórico lo vencido antes de leer

    ahora = ahora_utc()
    radio_m = RADIO_ZONA_KM * 1000
    lat_min, lat_max, lon_min, lon_max = caja(lat, lon, radio_m)
    consulta = (
        select(Reporte)
        .options(joinedload(Reporte.tipo_dano), joinedload(Reporte.colonia))
        .where(
            Reporte.lat.between(lat_min, lat_max),
            Reporte.lon.between(lon_min, lon_max),
            or_(
                and_(Reporte.categoria == "bache", Reporte.estado.in_(ESTADOS_BACHE_ABIERTOS)),
                and_(Reporte.categoria == "encharcamiento", Reporte.estado == "activo", Reporte.vigente_hasta > ahora),
            ),
        )
    )
    pares = [(r, distancia_m(lat, lon, r.lat, r.lon)) for r in db.scalars(consulta)]
    dentro = [(r, d) for r, d in pares if d <= radio_m]
    # False va antes que True: con la llave (no es intransitable, distancia) los intransitables quedan al inicio
    dentro.sort(key=lambda par: (par[0].nivel_agua != "intransitable", par[1]))

    hoy = a_hora_local(ahora).date()
    items = [a_cercano(r, hoy, d) for r, d in dentro[:MAX_RESULTADOS_ZONA]]
    return ZonaRespuesta(centro=PuntoZona(lat=lat, lon=lon), radio_m=radio_m, total=len(dentro), items=items)
