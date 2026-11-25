"""Folios consecutivos por categoría y año: BCH-2026-000123, ENC-2026-000045 (RN-03).

El consecutivo vive en la tabla folio_contadores (una fila por prefijo y año). Para que dos reportes creados al
mismo tiempo no reciban el mismo número, la fila se lee con SELECT ... FOR UPDATE: en PostgreSQL la segunda
transacción espera a que la primera termine. (SQLite no tiene bloqueo de fila, pero en las pruebas no hay
concurrencia; además reportes.folio es UNIQUE como última defensa.)

Uso dentro del servicio que crea el reporte, ANTES del commit:
    folio = generar_folio(db, prefijo_de("bache"), hoy_local().year)
El bloqueo se libera con el commit (o rollback) de la petición.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.reglas import PREFIJOS_FOLIO
from app.models import FolioContador


def prefijo_de(categoria: str) -> str:
    """"bache" -> "BCH", "encharcamiento" -> "ENC"."""
    return PREFIJOS_FOLIO[categoria]


def formatear_folio(prefijo: str, anio: int, numero: int) -> str:
    return f"{prefijo}-{anio}-{numero:06d}"


def _contador_bloqueado(db: Session, prefijo: str, anio: int) -> FolioContador | None:
    consulta = (
        select(FolioContador)
        .where(FolioContador.prefijo == prefijo, FolioContador.anio == anio)
        .with_for_update()
    )
    return db.scalar(consulta)


def generar_folio(db: Session, prefijo: str, anio: int) -> str:
    """Reserva el siguiente número para ese prefijo y año y devuelve el folio. No hace commit."""
    if prefijo not in PREFIJOS_FOLIO.values():
        raise ValueError(f"Prefijo de folio desconocido: {prefijo}")
    contador = _contador_bloqueado(db, prefijo, anio)
    if contador is None:
        # Primer folio del año. Si otra petición crea la fila al mismo tiempo, la llave primaria lo impide;
        # el savepoint (begin_nested) deja deshacer solo este intento y volver a leer la fila ya creada.
        try:
            with db.begin_nested():
                db.add(FolioContador(prefijo=prefijo, anio=anio, ultimo=0))
        except IntegrityError:
            pass
        contador = _contador_bloqueado(db, prefijo, anio)
    contador.ultimo += 1
    db.flush()
    return formatear_folio(prefijo, anio, contador.ultimo)
