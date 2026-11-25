"""Clima: aviso de lluvia (público). Sin lógica: todo está en el servicio."""

from fastapi import APIRouter

from app.schemas.clima import AvisoLluvia
from app.services import clima

router = APIRouter(prefix="/api/clima", tags=["Clima"])


@router.get("/aviso", response_model=AvisoLluvia, summary="Aviso de lluvia de las próximas 12 horas")
def aviso_de_lluvia():
    """Toma la **probabilidad máxima de lluvia** de las próximas 12 horas en Ciudad Juárez (Open-Meteo) y avisa si
    llega al umbral (30 %). El pronóstico se guarda 1 hora en memoria.

    Si Open-Meteo falla, tarda más de 5 s o responde algo inválido, la API **no** devuelve error: responde 200 con
    `{"disponible": false, ...}` y la pantalla muestra «Pronóstico no disponible»."""
    return clima.obtener_aviso()
