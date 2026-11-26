"""Validaciones comunes al alta de baches y de encharcamientos (y a la edición).

Están aparte para que services/reportes.py y services/encharcamientos.py las compartan sin importarse entre sí.
"""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errores import ErrorApi, error_validacion
from app.core.geo import dentro_del_municipio
from app.core.reglas import MAX_REPORTES_POR_HORA
from app.models import Colonia, Reporte, Usuario


def validar_municipio(lat: float, lon: float) -> None:
    """RN-01: 422 FUERA_DEL_MUNICIPIO si el punto no cae en Juárez (HU-02.1 CA2)."""
    if not dentro_del_municipio(lat, lon):
        raise ErrorApi(
            422,
            "FUERA_DEL_MUNICIPIO",
            "La ubicación está fuera del municipio de Juárez. Liebre Urbana solo recibe reportes de Ciudad Juárez",
        )


def validar_colonia(db: Session, colonia_id: int) -> Colonia:
    """La colonia debe existir y estar activa (las desactivadas se conservan solo para reportes anteriores)."""
    colonia = db.get(Colonia, colonia_id)
    if colonia is None or not colonia.activa:
        raise error_validacion({"colonia_id": "Elige una colonia de la lista"})
    return colonia


def validar_limite_horario(db: Session, autor: Usuario, ahora: datetime) -> None:
    """429 LIMITE_HORARIO si la cuenta ya creó MAX_REPORTES_POR_HORA reportes en la última hora.

    Se cuenta en la base de datos (no en memoria) para que el límite valga aunque el servidor se reinicie o
    corra en varios procesos. Cuentan baches y encharcamientos juntos.

    Antes de contar se bloquea la fila de la persona (SELECT ... FOR UPDATE): si llegan dos altas de la misma
    cuenta al mismo tiempo, la segunda espera a que la primera haga commit y su conteo ya incluye ese reporte.
    Sin el bloqueo, una ráfaga de peticiones simultáneas pasaba toda el límite. El bloqueo se libera con el
    commit (o rollback) del servicio de alta. Orden de bloqueos en el alta: primero esta fila del usuario y
    después la del contador de folios (generar_folio); siempre el mismo, para no bloquearse entre peticiones.
    SQLite (las pruebas) no tiene bloqueo de fila: ahí solo se comprueba que la consulta lo pida.
    """
    db.get(Usuario, autor.id, with_for_update=True, populate_existing=True)
    hace_una_hora = ahora - timedelta(hours=1)
    creados = db.scalar(
        select(func.count()).select_from(Reporte).where(Reporte.autor_id == autor.id, Reporte.creado_en > hace_una_hora)
    )
    if creados >= MAX_REPORTES_POR_HORA:
        raise ErrorApi(
            429,
            "LIMITE_HORARIO",
            f"Llegaste al límite de {MAX_REPORTES_POR_HORA} reportes por hora. Intenta de nuevo más tarde",
        )
