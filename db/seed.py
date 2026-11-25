"""Datos iniciales y de demostración (todos FICTICIOS).

Uso, desde la raíz del repositorio y con la base ya migrada (alembic -c db/alembic.ini upgrade head):
    python db/seed.py

Es idempotente: se puede correr varias veces y solo agrega lo que falta (busca cada registro por su
código, nombre o correo). Está dividido en funciones `sembrar_*` para que otros PRs agreguen las suyas
(colonias en L4/L5, reportes en L5) sin reescribir este archivo: basta con sumarlas a SEMBRADORES.

Contraseñas de las cuentas de demostración: variables SEED_CIUDADANO_PASSWORD, SEED_MODERADOR_PASSWORD y
SEED_COORDINADOR_PASSWORD. En desarrollo, si faltan, se usa CONTRASENA_DEMO (pública, escrita en el README y que
no se usa en ningún otro lado). En producción son obligatorias.
"""

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
from app.models import MotivoRechazo, Sector, TipoDano, Usuario, normalizar_correo  # noqa: E402

# Contraseña de demostración SOLO para desarrollo. Es pública: no la uses para nada real.
CONTRASENA_DEMO = "LiebreDemo2026"

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


# Orden en que se ejecutan. Otros PRs agregan aquí sus funciones (por ejemplo sembrar_colonias, sembrar_reportes).
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
