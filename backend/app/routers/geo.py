"""Ubicación: buscar una dirección y la búsqueda inversa (públicas). Sin lógica: todo está en el servicio."""

from fastapi import APIRouter, Query

from app.core.deps import SesionDB
from app.core.reglas import GEO_BUSQUEDA_MAX
from app.schemas.comun import respuestas_error
from app.schemas.geo import GeoBusqueda, GeoResultado
from app.services import geocodificacion

router = APIRouter(prefix="/api/geo", tags=["Ubicación"])

RESPUESTA_503 = {503: {"description": "`SERVICIO_NO_DISPONIBLE`: Nominatim no responde; captura la ubicación a mano"}}


@router.get(
    "/buscar",
    response_model=GeoBusqueda,
    summary="Buscar una dirección",
    responses={**respuestas_error(422), **RESPUESTA_503},
)
def buscar_direccion(
    db: SesionDB,
    q: str = Query("", max_length=GEO_BUSQUEDA_MAX, description="Dirección, por ejemplo «Av. Tecnológico 1340»"),
):
    """Hasta 5 lugares **dentro de Ciudad Juárez** con su calle y, si coincide con el catálogo, su colonia.

    Si no hay coincidencias responde `{"resultados": []}` (no es un error). Se llama al pulsar «Buscar»,
    nunca mientras la persona escribe (Nominatim permite 1 petición por segundo)."""
    return GeoBusqueda(resultados=geocodificacion.buscar(db, q))


@router.get(
    "/inversa",
    response_model=GeoResultado,
    summary="Calle y colonia de unas coordenadas",
    responses={**respuestas_error(422), **RESPUESTA_503},
)
def buscar_inversa(
    db: SesionDB,
    lat: float = Query(ge=-90, le=90, description="Latitud en grados, por ejemplo 31.7"),
    lon: float = Query(ge=-180, le=180, description="Longitud en grados, por ejemplo -106.4"),
):
    """Para el botón «Usar mi ubicación»: devuelve calle y colonia del punto. `dentro_del_municipio` avisa si el
    punto está fuera de Juárez (RN-01); en ese caso el reporte se rechazaría con 422 `FUERA_DEL_MUNICIPIO`."""
    return geocodificacion.inversa(db, lat, lon)
