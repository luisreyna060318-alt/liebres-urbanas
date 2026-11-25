"""Paginación común: ?pagina=1&tam=20 -> {"items": [...], "total": 137, "pagina": 1, "tam": 20}."""

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


def paginar(db: Session, consulta: Select, pagina: int, tam: int) -> dict:
    """Ejecuta la consulta para una página y cuenta el total sin paginar.

    La consulta debe traer ya su orden (order_by) para que las páginas sean estables.
    Devuelve un diccionario listo para el esquema Pagina[...].
    """
    total = db.scalar(select(func.count()).select_from(consulta.order_by(None).subquery()))
    items = list(db.scalars(consulta.limit(tam).offset((pagina - 1) * tam)))
    return {"items": items, "total": total, "pagina": pagina, "tam": tam}
