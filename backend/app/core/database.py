"""Conexión a la base de datos con SQLAlchemy 2."""

from collections.abc import Iterator

from sqlalchemy import Engine, MetaData, create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# Nombres predecibles para índices y restricciones: así Alembic puede crearlos y borrarlos sin ambigüedad.
convencion_nombres = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Clase de la que heredan todos los modelos."""

    metadata = MetaData(naming_convention=convencion_nombres)


def crear_engine(url: str | URL, **opciones) -> Engine:
    """Crea el engine. Con SQLite (pruebas) activa las llaves foráneas, que SQLite trae apagadas."""
    engine = create_engine(url, pool_pre_ping=True, **opciones)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _activar_llaves_foraneas(conexion, _registro):
            conexion.execute("PRAGMA foreign_keys=ON")

    return engine


engine = crear_engine(settings.sqlalchemy_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión de base de datos por petición, que siempre se cierra."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
