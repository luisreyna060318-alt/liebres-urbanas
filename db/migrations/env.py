"""Entorno de Alembic: conecta las migraciones con nuestros modelos y nuestra base de datos.

Se ejecuta desde la raíz del repositorio:
    alembic -c db/alembic.ini upgrade head       # aplica todo
    alembic -c db/alembic.ini downgrade base     # deshace todo (borra las tablas)
La base sale de la variable DATABASE_URL (ver backend/app/core/config.py).
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context

# Para poder importar "app" (que vive en backend/) desde esta carpeta
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app import models  # noqa: E402,F401  (importar los modelos los registra en Base.metadata)
from app.core.config import settings  # noqa: E402
from app.core.database import Base, crear_engine  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Alembic compara esta metadata con la base de datos al generar migraciones (--autogenerate)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Genera el SQL sin conectarse (alembic -c db/alembic.ini upgrade head --sql)."""
    context.configure(
        url=settings.sqlalchemy_url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica las migraciones conectándose a la base de datos."""
    engine = crear_engine(settings.sqlalchemy_url)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite no sabe hacer ALTER TABLE completo: "batch" recrea la tabla cuando hace falta
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
