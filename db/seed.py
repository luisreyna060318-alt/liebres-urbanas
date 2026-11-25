"""Datos iniciales y de demostración (todos FICTICIOS).

Uso, desde la raíz del repositorio y con la base ya migrada (alembic -c db/alembic.ini upgrade head):
    python db/seed.py

Es idempotente: se puede correr varias veces y solo agrega lo que falta (busca cada registro por su
código, nombre o correo). Orden de ejecución (sembrar_todo): catálogos y cuentas de demostración (SEMBRADORES),
colonias reales desde db/datos/colonias_juarez.csv (cargar_colonias) y 500 reportes ficticios (cargar_reportes_demo).

Contraseñas de las cuentas de demostración: variables SEED_CIUDADANO_PASSWORD, SEED_MODERADOR_PASSWORD y
SEED_COORDINADOR_PASSWORD. En desarrollo, si faltan, se usa CONTRASENA_DEMO (pública, escrita en el README y que
no se usa en ningún otro lado). En producción son obligatorias.
"""

import csv
import sys
from pathlib import Path

# Para poder importar "app" (que vive en backend/)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.core.tiempo import ahora_utc  # noqa: E402
from app.models import Colonia, MotivoRechazo, Sector, TipoDano, Usuario, normalizar_correo  # noqa: E402

# Contraseña de demostración SOLO para desarrollo. Es pública: no la uses para nada real.
CONTRASENA_DEMO = "LiebreDemo2026"

# Catálogo de colonias reales de Juárez (RNF-09). Lo prepara y documenta (fuente) el equipo en db/datos/.
RUTA_COLONIAS = Path(__file__).resolve().parent / "datos" / "colonias_juarez.csv"
ENCABEZADO_COLONIAS = ["cp", "nombre", "tipo_asentamiento", "sector", "lat", "lon"]
FUENTE_COLONIAS = "SEPOMEX/Correos de México; coordenadas aproximadas OpenStreetMap"
# Caja amplia alrededor del municipio de Juárez: solo detecta errores de captura (lat/lon invertidas o con signo mal)
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = 30.5, 32.5, -107.5, -105.0

SECTORES = ["Centro", "Norponiente", "Nororiente", "Surponiente", "Suroriente"]

TIPOS_DANO = [  # (código, nombre)
    ("bache", "Bache"),
    ("hundimiento", "Hundimiento"),
    ("grieta", "Grieta"),
    ("alcantarilla_sin_tapa", "Alcantarilla sin tapa"),
]

MOTIVOS_RECHAZO = [  # (código, nombre, pide_explicacion)
    ("duplicado", "Duplicado", False),
    ("fuera_del_municipio", "Fuera del municipio", False),
    ("no_es_via_publica", "No es vía pública", False),
    ("contenido_inapropiado", "Contenido inapropiado", False),
    ("otro", "Otro", True),
]

CUENTAS_DEMO = [  # (rol, nombre, correo, variable de entorno con la contraseña)
    ("ciudadano", "Ciudadana de Demostración", "ciudadano@liebreurbana.test", "seed_ciudadano_password"),
    ("moderador", "Moderador de Demostración", "moderador@liebreurbana.test", "seed_moderador_password"),
    ("coordinador", "Coordinadora de Demostración", "coordinador@liebreurbana.test", "seed_coordinador_password"),
]


def sembrar_sectores(db: Session) -> int:
    existentes = set(db.scalars(select(Sector.nombre)))
    nuevos = [Sector(nombre=nombre) for nombre in SECTORES if nombre not in existentes]
    db.add_all(nuevos)
    return len(nuevos)


def sembrar_tipos_dano(db: Session) -> int:
    existentes = set(db.scalars(select(TipoDano.codigo)))
    nuevos = [TipoDano(codigo=c, nombre=n) for c, n in TIPOS_DANO if c not in existentes]
    db.add_all(nuevos)
    return len(nuevos)


def sembrar_motivos_rechazo(db: Session) -> int:
    existentes = set(db.scalars(select(MotivoRechazo.codigo)))
    nuevos = [
        MotivoRechazo(codigo=c, nombre=n, pide_explicacion=pide)
        for c, n, pide in MOTIVOS_RECHAZO
        if c not in existentes
    ]
    db.add_all(nuevos)
    return len(nuevos)


def contrasena_de(variable: str) -> str:
    """Contraseña de una cuenta de demostración: de la variable de entorno o, solo en desarrollo, la de demo."""
    valor = getattr(settings, variable)
    if valor:
        return valor
    if settings.es_produccion:
        raise SystemExit(f"En producción define {variable.upper()} para crear la cuenta de demostración")
    return CONTRASENA_DEMO


def sembrar_cuentas_demo(db: Session) -> int:
    creadas = 0
    for rol, nombre, correo, variable in CUENTAS_DEMO:
        existe = db.scalar(select(Usuario.id).where(func.lower(Usuario.correo) == normalizar_correo(correo)))
        if existe:
            continue
        db.add(
            Usuario(
                nombre=nombre,
                correo=correo,
                password_hash=hash_password(contrasena_de(variable)),
                rol=rol,
                acepto_privacidad_en=ahora_utc(),
            )
        )
        creadas += 1
    return creadas


class ErrorSemilla(Exception):
    """Falla de la semilla con un mensaje pensado para quien la corre (qué falta y cómo arreglarlo)."""


def _leer_numero(texto: str, nombre: str, linea: int, minimo: float, maximo: float) -> float:
    try:
        valor = float(texto)
    except (TypeError, ValueError):
        raise ErrorSemilla(f"colonias: línea {linea}, «{nombre}» no es un número: {texto!r}") from None
    if not minimo <= valor <= maximo:
        raise ErrorSemilla(f"colonias: línea {linea}, «{nombre}» fuera de Ciudad Juárez ({valor}); ¿lat/lon al revés?")
    return valor


def cargar_colonias(db: Session, ruta_csv: Path | str | None = None) -> int:
    """Carga las colonias del CSV (UTF-8, encabezado exacto cp,nombre,tipo_asentamiento,sector,lat,lon).

    Idempotente: la clave es (sector, nombre), igual que la restricción UNIQUE de la tabla; una colonia que ya
    existe no se duplica (solo se le completan lat, lon y fuente si no los tenía). Devuelve cuántas agregó.
    Los sectores deben existir (los crea sembrar_sectores), así un error de captura no inventa sectores nuevos.
    """
    ruta = Path(ruta_csv) if ruta_csv else RUTA_COLONIAS
    if not ruta.is_file():
        raise ErrorSemilla(
            f"Falta el catálogo de colonias: {ruta}. Debe ser un CSV UTF-8 con el encabezado "
            f"{','.join(ENCABEZADO_COLONIAS)} (lo genera la rama feature/l4-catalogo-colonias)."
        )

    sectores = {s.nombre: s.id for s in db.scalars(select(Sector))}
    existentes = {(c.sector_id, c.nombre): c for c in db.scalars(select(Colonia))}
    agregadas = 0
    # utf-8-sig tolera el BOM que agrega Excel al guardar como "CSV UTF-8"
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        if lector.fieldnames != ENCABEZADO_COLONIAS:
            raise ErrorSemilla(
                f"{ruta.name}: el encabezado debe ser exactamente {','.join(ENCABEZADO_COLONIAS)} "
                f"y es {','.join(lector.fieldnames or [])}"
            )
        for fila in lector:
            linea = lector.line_num
            nombre = (fila["nombre"] or "").strip()
            sector = (fila["sector"] or "").strip()
            if not nombre or len(nombre) > 120:
                raise ErrorSemilla(f"colonias: línea {linea}, el nombre está vacío o pasa de 120 caracteres")
            if sector not in sectores:
                raise ErrorSemilla(
                    f"colonias: línea {linea}, sector desconocido {sector!r}; los válidos son {', '.join(sectores)}"
                )
            lat = _leer_numero(fila["lat"], "lat", linea, LAT_MIN, LAT_MAX)
            lon = _leer_numero(fila["lon"], "lon", linea, LON_MIN, LON_MAX)

            clave = (sectores[sector], nombre)
            colonia = existentes.get(clave)
            if colonia is None:
                colonia = Colonia(nombre=nombre, sector_id=clave[0], lat=lat, lon=lon, fuente=FUENTE_COLONIAS)
                db.add(colonia)
                existentes[clave] = colonia  # por si el CSV repite la fila
                agregadas += 1
            elif colonia.lat is None:
                colonia.lat, colonia.lon, colonia.fuente = lat, lon, FUENTE_COLONIAS
    return agregadas


# Orden en que se ejecutan los sembradores de catálogos y cuentas (cada uno devuelve cuántos registros agregó).
SEMBRADORES = [
    ("sectores", sembrar_sectores),
    ("tipos de daño", sembrar_tipos_dano),
    ("motivos de rechazo", sembrar_motivos_rechazo),
    ("cuentas de demostración", sembrar_cuentas_demo),
]


def sembrar(db: Session) -> dict[str, int]:
    """Ejecuta todos los sembradores en una sola transacción y devuelve cuántos registros agregó cada uno."""
    resumen = {}
    for nombre, funcion in SEMBRADORES:
        resumen[nombre] = funcion(db)
        db.flush()  # asigna ids por si el siguiente sembrador los necesita
    db.commit()
    return resumen


def main() -> None:
    with SessionLocal() as db:
        for nombre, agregados in sembrar(db).items():
            print(f"  {nombre}: {agregados} nuevos")


if __name__ == "__main__":
    main()
