"""Salud del servicio y reglas de negocio públicas."""

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core import reglas
from app.core.deps import SesionDB
from app.core.errores import ErrorApi
from app.schemas.comun import ReglasSalida

router = APIRouter(prefix="/api", tags=["Sistema"])


@router.get("/health", summary="Salud del servicio")
def salud(db: SesionDB):
    """Responde `{"estado": "ok", "base_de_datos": "ok"}` si la API y la base de datos responden.

    Lo usan Render y Docker para saber si el contenedor está listo (RNF-03)."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise ErrorApi(503, "SERVICIO_NO_DISPONIBLE", "La base de datos no responde") from None
    return {"estado": "ok", "base_de_datos": "ok"}


@router.get("/reglas", response_model=ReglasSalida, summary="Reglas de negocio")
def obtener_reglas():
    """Valores documentados de las reglas (distancias, vigencia, límites, sesión...).

    El frontend los pide aquí en lugar de repetirlos, así cliente y servidor validan con los mismos números."""
    return ReglasSalida(
        radio_duplicado_bache_m=reglas.RADIO_DUPLICADO_BACHE_M,
        radio_duplicado_encharcamiento_m=reglas.RADIO_DUPLICADO_ENCHARCAMIENTO_M,
        vigencia_encharcamiento_horas=reglas.VIGENCIA_ENCHARCAMIENTO_HORAS,
        desmentidos_para_cerrar=reglas.DESMENTIDOS_PARA_CERRAR,
        radio_zona_km=reglas.RADIO_ZONA_KM,
        max_reportes_por_hora=reglas.MAX_REPORTES_POR_HORA,
        descripcion_max=reglas.DESCRIPCION_MAX,
        password_min=reglas.PASSWORD_MIN,
        inactividad_min=reglas.INACTIVIDAD_MIN,
        tam_pagina_consulta=reglas.TAM_PAGINA_CONSULTA,
        tam_pagina_mis_reportes=reglas.TAM_PAGINA_MIS_REPORTES,
        umbral_lluvia_pct=reglas.UMBRAL_LLUVIA_PCT,
        zona_horaria=reglas.ZONA_HORARIA,
    )
