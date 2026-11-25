"""Fechas y horas (RN-02).

Regla del proyecto: en la base y en la API todo va en UTC "con zona" (aware). Solo para mostrar o para decidir
"qué día es hoy en Juárez" se convierte a America/Ciudad_Juarez.

Cuidado con SQLite (lo usan las pruebas): no guarda la zona horaria y devuelve fechas "sin zona" (naive).
Por eso las columnas de fecha y hora usan el tipo FechaHoraUTC, que guarda en UTC y devuelve siempre en UTC.
"""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator

from app.core.reglas import ZONA_HORARIA

ZONA_JUAREZ = ZoneInfo(ZONA_HORARIA)


def ahora_utc() -> datetime:
    """Fecha y hora actual en UTC, con zona."""
    return datetime.now(UTC)


def como_utc(valor: datetime) -> datetime:
    """Pasa cualquier fecha a UTC con zona. Una fecha sin zona se interpreta como UTC (así la devuelve SQLite)."""
    if valor.tzinfo is None:
        return valor.replace(tzinfo=UTC)
    return valor.astimezone(UTC)


def a_hora_local(valor: datetime) -> datetime:
    """Convierte a la hora de Ciudad Juárez, para mostrar o para calcular días."""
    return como_utc(valor).astimezone(ZONA_JUAREZ)


def hoy_local() -> date:
    """La fecha de hoy en Ciudad Juárez (no en UTC: a las 18:00 de Juárez en UTC ya es mañana)."""
    return ahora_utc().astimezone(ZONA_JUAREZ).date()


class FechaHoraUTC(TypeDecorator):
    """Columna de fecha y hora que siempre entra y sale en UTC con zona, en PostgreSQL y en SQLite."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return como_utc(value) if value is not None else None

    def process_result_value(self, value, dialect):
        return como_utc(value) if value is not None else None
