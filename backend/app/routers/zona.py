"""¿Cómo está mi zona? (público). Sin lógica: todo está en el servicio."""

from fastapi import APIRouter, Query

from app.core.deps import SesionDB
from app.schemas.comun import respuestas_error
from app.schemas.zona import ZonaRespuesta
from app.services import zona as zona_service

router = APIRouter(prefix="/api", tags=["Zona"])


@router.get(
    "/zona",
    response_model=ZonaRespuesta,
    summary="¿Cómo está mi zona?",
    responses=respuestas_error(422),
)
def como_esta_mi_zona(
    db: SesionDB,
    lat: float = Query(ge=-90, le=90, description="Latitud del punto, por ejemplo 31.7"),
    lon: float = Query(ge=-180, le=180, description="Longitud del punto, por ejemplo -106.4"),
):
    """Reportes **activos** a 1 km o menos del punto: baches abiertos y encharcamientos activos y vigentes.

    Los encharcamientos `intransitable` van al inicio; el resto, del más cercano al más lejano, con `distancia_m`.
    Devuelve hasta 50 y `total` dice cuántos hay en realidad. Nunca incluye al autor.
    Fuera de Juárez → 422 `FUERA_DEL_MUNICIPIO`."""
    return zona_service.consultar_zona(db, lat, lon)
