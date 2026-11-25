"""Lecturas de catálogos para los formularios: sectores, colonias, tipos de daño y motivos de rechazo."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.paginacion import paginar
from app.models import Colonia, MotivoRechazo, Sector, TipoDano


def listar_sectores(db: Session) -> list[Sector]:
    return list(db.scalars(select(Sector).order_by(Sector.nombre)))


def listar_colonias(
    db: Session, q: str | None, sector_id: int | None, solo_activas: bool, pagina: int, tam: int
) -> dict:
    """Colonias en orden alfabético, con su sector. `q` busca por nombre sin distinguir mayúsculas."""
    consulta = select(Colonia).options(joinedload(Colonia.sector)).order_by(Colonia.nombre, Colonia.id)
    if q and q.strip():
        # Parámetro de SQLAlchemy: el texto nunca se pega a mano en el SQL (sin inyección)
        consulta = consulta.where(func.lower(Colonia.nombre).contains(q.strip().lower()))
    if sector_id is not None:
        consulta = consulta.where(Colonia.sector_id == sector_id)
    if solo_activas:
        consulta = consulta.where(Colonia.activa.is_(True))
    return paginar(db, consulta, pagina, tam)


def listar_tipos_dano(db: Session) -> list[TipoDano]:
    """Solo los activos: los desactivados se conservan para los reportes anteriores (HU-06.3)."""
    return list(db.scalars(select(TipoDano).where(TipoDano.activo.is_(True)).order_by(TipoDano.id)))


def listar_motivos_rechazo(db: Session) -> list[MotivoRechazo]:
    return list(db.scalars(select(MotivoRechazo).where(MotivoRechazo.activo.is_(True)).order_by(MotivoRechazo.id)))
