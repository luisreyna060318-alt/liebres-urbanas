"""Lecturas de catálogos para los formularios: sectores, colonias, tipos de daño y motivos de rechazo."""

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.errores import ErrorApi, error_validacion
from app.core.geo import dentro_del_municipio
from app.core.paginacion import paginar
from app.core.reglas import FUENTE_COLONIA_MANUAL
from app.models import Colonia, MotivoRechazo, Reporte, Sector, TipoDano, UsuarioColonia
from app.schemas.catalogos import ColoniaActualizacion, ColoniaEntrada, SectorEntrada


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


# --- Administración de sectores y colonias (HU-06.1, solo coordinador) ---------------------------------
def _sector_duplicado() -> ErrorApi:
    return ErrorApi(409, "SECTOR_DUPLICADO", "Ya existe un sector con ese nombre. Elige otro nombre")


def _colonia_duplicada() -> ErrorApi:
    return ErrorApi(409, "COLONIA_DUPLICADA", "Ese sector ya tiene una colonia con ese nombre. Elige otro nombre")


def crear_sector(db: Session, datos: SectorEntrada) -> Sector:
    _revisar_nombre_de_sector(db, datos.nombre, None)
    sector = Sector(nombre=datos.nombre)
    db.add(sector)
    _guardar(db, _sector_duplicado)
    return sector


def actualizar_sector(db: Session, sector_id: int, datos: SectorEntrada) -> Sector:
    sector = _sector_o_404(db, sector_id)
    _revisar_nombre_de_sector(db, datos.nombre, sector.id)
    sector.nombre = datos.nombre
    _guardar(db, _sector_duplicado)
    return sector


def crear_colonia(db: Session, datos: ColoniaEntrada) -> Colonia:
    _sector_existente(db, datos.sector_id)
    _validar_coordenadas(datos.lat, datos.lon)
    _revisar_nombre_de_colonia(db, datos.nombre, datos.sector_id, None)
    colonia = Colonia(
        nombre=datos.nombre, sector_id=datos.sector_id, lat=datos.lat, lon=datos.lon, fuente=FUENTE_COLONIA_MANUAL
    )
    db.add(colonia)
    _guardar(db, _colonia_duplicada)
    return _colonia_con_sector(db, colonia.id)


def actualizar_colonia(db: Session, colonia_id: int, datos: ColoniaActualizacion) -> Colonia:
    colonia = _colonia_o_404(db, colonia_id)
    _sector_existente(db, datos.sector_id)
    _validar_coordenadas(datos.lat, datos.lon)
    _revisar_nombre_de_colonia(db, datos.nombre, datos.sector_id, colonia.id)
    colonia.nombre, colonia.sector_id, colonia.activa = datos.nombre, datos.sector_id, datos.activa
    colonia.lat, colonia.lon = datos.lat, datos.lon
    _guardar(db, _colonia_duplicada)
    return _colonia_con_sector(db, colonia.id)


def borrar_colonia(db: Session, colonia_id: int) -> None:
    """Una colonia con reportes no se borra (los reportes la necesitan): solo se desactiva (HU-06.1 CA2)."""
    colonia = _colonia_o_404(db, colonia_id)
    reportes = db.scalar(select(func.count()).select_from(Reporte).where(Reporte.colonia_id == colonia.id))
    if reportes:
        raise ErrorApi(
            409,
            "COLONIA_CON_REPORTES",
            f"Esta colonia tiene {reportes} reportes y no se puede eliminar. Desactívala para que deje de ofrecerse",
        )
    # Las colonias de interés de las personas apuntan a ésta: se quitan primero (en PostgreSQL ya iría en cascada)
    db.execute(delete(UsuarioColonia).where(UsuarioColonia.colonia_id == colonia.id))
    db.delete(colonia)
    try:
        db.commit()
    except IntegrityError:
        # Carrera: alguien creó un reporte en esta colonia entre el conteo y el borrado. La llave foránea de
        # `reportes` lo impide; se responde el mismo 409 en lugar de un 500.
        db.rollback()
        raise ErrorApi(
            409,
            "COLONIA_CON_REPORTES",
            "Esta colonia tiene reportes y no se puede eliminar. Desactívala para que deje de ofrecerse",
        ) from None


def _sector_o_404(db: Session, sector_id: int) -> Sector:
    sector = db.get(Sector, sector_id)
    if sector is None:
        raise ErrorApi(404, "NO_ENCONTRADO", "Ese sector no existe")
    return sector


def _colonia_o_404(db: Session, colonia_id: int) -> Colonia:
    colonia = db.get(Colonia, colonia_id)
    if colonia is None:
        raise ErrorApi(404, "NO_ENCONTRADO", "Esa colonia no existe")
    return colonia


def _colonia_con_sector(db: Session, colonia_id: int) -> Colonia:
    return db.scalars(select(Colonia).options(joinedload(Colonia.sector)).where(Colonia.id == colonia_id)).one()


def _sector_existente(db: Session, sector_id: int) -> None:
    if db.get(Sector, sector_id) is None:
        raise error_validacion({"sector_id": "El sector no existe"})


def _validar_coordenadas(lat: float | None, lon: float | None) -> None:
    """Van las dos o ninguna, y dentro del municipio de Juárez (RN-01)."""
    if lat is None and lon is None:
        return
    if lat is None or lon is None:
        faltante = "lat" if lat is None else "lon"
        raise error_validacion({faltante: "Captura latitud y longitud juntas, o deja las dos vacías"})
    if not dentro_del_municipio(lat, lon):
        raise error_validacion(
            {"lat": "Las coordenadas deben estar dentro de Ciudad Juárez", "lon": "Revisa que sean de Ciudad Juárez"}
        )


def _revisar_nombre_de_sector(db: Session, nombre: str, propio_id: int | None) -> None:
    consulta = select(Sector.id).where(func.lower(Sector.nombre) == nombre.lower())
    if propio_id is not None:
        consulta = consulta.where(Sector.id != propio_id)
    if db.scalar(consulta) is not None:
        raise _sector_duplicado()


def _revisar_nombre_de_colonia(db: Session, nombre: str, sector_id: int, propia_id: int | None) -> None:
    """Sin distinguir mayúsculas dentro del mismo sector (HU-06.1 CA3); en otro sector el nombre sí puede repetirse."""
    consulta = select(Colonia.id).where(Colonia.sector_id == sector_id, func.lower(Colonia.nombre) == nombre.lower())
    if propia_id is not None:
        consulta = consulta.where(Colonia.id != propia_id)
    if db.scalar(consulta) is not None:
        raise _colonia_duplicada()


def _guardar(db: Session, error_duplicado) -> None:
    """Confirma los cambios. Si dos coordinadores guardan el mismo nombre a la vez, la restricción única de la
    base lo detecta aunque la revisión previa no lo haya visto."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise error_duplicado() from None
