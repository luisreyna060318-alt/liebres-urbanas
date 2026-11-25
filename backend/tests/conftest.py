"""Configuración común de las pruebas.

Usan SQLite en memoria (rápido, sin Docker ni .env): los valores de prueba se ponen ANTES de importar la app.
"""

import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import Annotated

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "clave-solo-para-pruebas-0123456789abcdef"
os.environ["ENTORNO"] = "desarrollo"

# Para importar db/seed.py en las pruebas de la semilla
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "db"))

import pytest  # noqa: E402
from fastapi import APIRouter, Depends  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import Base, crear_engine, get_db  # noqa: E402
from app.core.deps import require_role  # noqa: E402
from app.core.security import crear_token, hash_password  # noqa: E402
from app.core.tiempo import ahora_utc  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Colonia, Reporte, Sector, TipoDano, Usuario  # noqa: E402

PASSWORD_PRUEBA = "Clave1234"
# Un hash bcrypt tarda ~0.2 s: se calcula una vez y se reutiliza en todos los usuarios de prueba
HASH_PRUEBA = hash_password(PASSWORD_PRUEBA)

# --- Rutas mínimas SOLO para probar require_role (no existen en la aplicación real) ---------------
router_pruebas = APIRouter(prefix="/api/_pruebas")


@router_pruebas.get("/solo-coordinador")
def _solo_coordinador(usuario: Annotated[Usuario, Depends(require_role("coordinador"))]):
    return {"rol": usuario.rol}


@router_pruebas.get("/moderacion")
def _moderacion(usuario: Annotated[Usuario, Depends(require_role("moderador", "coordinador"))]):
    return {"rol": usuario.rol}


@router_pruebas.get("/solo-ciudadano")
def _solo_ciudadano(usuario: Annotated[Usuario, Depends(require_role("ciudadano"))]):
    return {"rol": usuario.rol}


app.include_router(router_pruebas)


# --- Fixtures -----------------------------------------------------------------------------------
@pytest.fixture()
def db():
    """Una base SQLite nueva y vacía para cada prueba."""
    engine = crear_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, autoflush=False)() as sesion:
        yield sesion
    engine.dispose()


@pytest.fixture()
def client(db):
    """Cliente HTTP de pruebas que usa la base de prueba."""

    def get_db_de_prueba():
        yield db

    app.dependency_overrides[get_db] = get_db_de_prueba
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


@pytest.fixture()
def crear_usuario(db):
    """Fábrica: crear_usuario("ana@ejemplo.test", rol="moderador", activo=False)."""

    def _crear(correo: str, rol: str = "ciudadano", activo: bool = True, nombre: str = "Persona de Prueba"):
        usuario = Usuario(nombre=nombre, correo=correo, password_hash=HASH_PRUEBA, rol=rol, activo=activo)
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario

    return _crear


def encabezado_de(usuario: Usuario, expira_en: timedelta | None = None) -> dict[str, str]:
    """Encabezado Authorization con un token de ese usuario."""
    return {"Authorization": f"Bearer {crear_token(usuario.id, expira_en)}"}


@pytest.fixture()
def ciudadano(crear_usuario):
    return crear_usuario("ciudadano@ejemplo.test", rol="ciudadano")


@pytest.fixture()
def moderador(crear_usuario):
    return crear_usuario("moderador@ejemplo.test", rol="moderador")


@pytest.fixture()
def coordinador(crear_usuario):
    return crear_usuario("coordinador@ejemplo.test", rol="coordinador")


@pytest.fixture()
def crear_reporte(db, ciudadano):
    """Fábrica de reportes válidos: crear_reporte("bache") o crear_reporte("encharcamiento", estado=...)."""
    sector = Sector(nombre="Sector de Prueba")
    tipo = TipoDano(codigo="bache", nombre="Bache")
    db.add_all([sector, tipo])
    db.flush()
    colonia = Colonia(nombre="Colonia de Prueba", sector_id=sector.id)
    db.add(colonia)
    db.commit()
    contador = {"n": 0}

    def _crear(categoria: str = "bache", estado: str | None = None, creado_en=None, **extra):
        contador["n"] += 1
        comunes = dict(autor_id=ciudadano.id, colonia_id=colonia.id, calle="Calle Ficticia", lat=31.7, lon=-106.4,
                       **extra)
        if creado_en is not None:
            comunes["creado_en"] = creado_en
        if categoria == "bache":
            reporte = Reporte(folio=f"BCH-2026-{contador['n']:06d}", categoria="bache", tipo_dano_id=tipo.id,
                              severidad="baja", tamano="chico", profundidad="baja", carril="orilla",
                              estado=estado or "recibido", **comunes)
        else:
            reporte = Reporte(folio=f"ENC-2026-{contador['n']:06d}", categoria="encharcamiento",
                              nivel_agua="cubre_carril", vigente_hasta=ahora_utc() + timedelta(hours=6),
                              estado=estado or "activo", **comunes)
        db.add(reporte)
        db.commit()
        return reporte

    return _crear
