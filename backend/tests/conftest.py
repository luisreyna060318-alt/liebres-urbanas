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
from app.services import geocodificacion  # noqa: E402

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
@pytest.fixture(autouse=True)
def sin_red(monkeypatch):
    """Ninguna prueba sale a internet: si algo intenta llamar a Nominatim sin simularlo, la prueba falla.
    También limpia la caché y el límite de ritmo para que cada prueba empiece igual."""

    def _prohibido(ruta, parametros):
        raise AssertionError(f"Prueba sin simular la red: se intentó llamar a Nominatim ({ruta})")

    geocodificacion.limpiar_estado()
    monkeypatch.setattr(geocodificacion, "_llamar_http", _prohibido)
    yield
    geocodificacion.limpiar_estado()


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


# --- Datos para las pruebas de reportes (L7 en adelante) -------------------------------------------
# Punto dentro de Ciudad Juárez. Para que dos reportes NO sean duplicados, sepáralos 0.001 grados de latitud
# (unos 111 m): punto(1), punto(2)...
LAT_BASE, LON_BASE = 31.7000, -106.4300


def punto(n: int = 0) -> tuple[float, float]:
    return LAT_BASE + n * 0.001, LON_BASE


@pytest.fixture()
def catalogo(db):
    """Sector, una colonia activa, una desactivada y los 4 tipos de daño. Devuelve un diccionario.
    (No combinar con el fixture crear_reporte, que crea su propio tipo "bache".)"""
    sector = Sector(nombre="Centro")
    db.add(sector)
    db.flush()
    colonia = Colonia(nombre="Partido Escobedo", sector_id=sector.id)
    inactiva = Colonia(nombre="Colonia Cerrada", sector_id=sector.id, activa=False)
    tipos = [
        TipoDano(codigo=codigo, nombre=nombre)
        for codigo, nombre in [
            ("bache", "Bache"),
            ("hundimiento", "Hundimiento"),
            ("grieta", "Grieta"),
            ("alcantarilla_sin_tapa", "Alcantarilla sin tapa"),
        ]
    ]
    db.add_all([colonia, inactiva, *tipos])
    db.commit()
    return {"sector": sector, "colonia": colonia, "inactiva": inactiva, "tipos": {t.codigo: t for t in tipos}}


def datos_bache(colonia_id: int, n: int = 0, /, **cambios) -> dict:
    """Cuerpo válido para POST /api/reportes/baches en punto(n); `cambios` reemplaza campos."""
    lat, lon = punto(n)
    datos = {
        "tipo_dano_codigo": "bache", "lat": lat, "lon": lon, "calle": "Av. Tecnológico", "colonia_id": colonia_id,
        "descripcion": "Hueco junto al semáforo", "tamano": "mediano", "profundidad": "media", "carril": "derecho",
        "senalizado": None, "forzar": False,
    }
    datos.update(cambios)
    return datos


# Llaves que NUNCA deben aparecer en una respuesta pública (RN-04) ni en ninguna respuesta (password_hash)
LLAVES_PROHIBIDAS = {"autor", "autor_id", "usuario_id", "correo", "nombre_autor", "password", "password_hash", "actor",
                     "actor_id"}


def llaves_de(valor) -> set[str]:
    """Todas las llaves de un JSON (recorre diccionarios y listas anidados)."""
    if isinstance(valor, dict):
        return set(valor) | set().union(*(llaves_de(v) for v in valor.values()))
    if isinstance(valor, list):
        return set().union(*(llaves_de(v) for v in valor)) if valor else set()
    return set()
