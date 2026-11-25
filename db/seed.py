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
import math
import random
import secrets
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

# Para poder importar "app" (que vive en backend/)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.geo import METROS_POR_GRADO_LAT  # noqa: E402
from app.core.reglas import CARRILES, VIGENCIA_ENCHARCAMIENTO_HORAS  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.core.tiempo import a_hora_local, ahora_utc, como_utc  # noqa: E402
from app.models import (  # noqa: E402
    Colonia,
    Confirmacion,
    HistorialEstado,
    MotivoRechazo,
    Reporte,
    Sector,
    TipoDano,
    Usuario,
    normalizar_correo,
)
from app.services.estados import puede_pasar  # noqa: E402
from app.services.folios import generar_folio, prefijo_de  # noqa: E402

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


# =====================================================================================================
# Reportes de demostración (RNF-09): 500 reportes FICTICIOS repartidos en 12 semanas.
# Salen siempre iguales (random.Random con semilla fija) para que la demo y las pruebas sean repetibles.
# Cada reporte trae su historial de estados armado con puede_pasar() (RN-05 y RN-06), así que el tablero
# y la consulta tienen datos coherentes: baches en todos los estados, algunos abiertos desde hace casi
# tres meses, 6 puntos de encharcamiento que se repiten y unos pocos encharcamientos activos.
# =====================================================================================================
TOTAL_REPORTES = 500
SEMANAS = 12
PORCENTAJE_ENCHARCAMIENTOS = 25  # el resto son baches
SEMILLA_DEMO = 2026

# Estado final de los baches (porcentaje). De los encharcamientos: unos activos, unos rechazados y el resto históricos.
PROPORCION_ESTADOS_BACHE = [
    ("recibido", 20), ("validado", 25), ("en_reparacion", 15), ("reparado", 30), ("rechazado", 10),
]
ENCHARCAMIENTOS_ACTIVOS = 4  # se crean hace pocas horas y vencen solos (en la demo se crea uno nuevo en vivo)
ENCHARCAMIENTOS_RECHAZADOS = 6
BACHES_ANTIGUOS = 14  # baches abiertos hace 58 a 80 días, para el tablero de longevidad
GRUPOS_DE_BACHES = 8  # baches cercanos entre sí, a lo largo de una calle
BACHES_POR_GRUPO = 4
REPORTES_POR_PUNTO = [4, 5, 6, 4, 5, 5]  # HU-03.4: 6 puntos que se encharcan en días distintos

CIUDADANOS_FICTICIOS = 30
DOMINIO_FICTICIO = "liebreurbana.test"
CORREO_CIUDADANO_DEMO = "ciudadano@liebreurbana.test"
CORREO_MODERADOR_DEMO = "moderador@liebreurbana.test"
CORREO_COORDINADOR_DEMO = "coordinador@liebreurbana.test"

PRIMEROS_NOMBRES = ["Ana", "Luis", "María", "Jorge", "Sofía", "Pedro", "Lucía", "Carlos", "Elena", "Raúl", "Paola",
                    "Diego", "Valeria", "Hugo", "Renata"]
APELLIDOS = ["Ramos", "Soto", "Vega", "Luna", "Ortiz", "Reyes", "Mora", "Pineda", "Salas", "Cano"]

# Nombres genéricos de calles: no corresponden a ninguna dirección real ni a datos personales
CALLES = ["Calle Primera", "Calle Segunda", "Calle Tercera", "Calle Cuarta", "Calle Quinta", "Calle Sexta",
          "Calle Décima", "Av. de las Torres", "Av. del Río", "Av. Principal", "Av. de los Maestros", "Av. Norte",
          "Calle del Sol", "Calle de la Luna", "Calle Pino", "Calle Nogal", "Calle Álamo", "Calle Fresno",
          "Calle Cedro", "Calle Girasol", "Calle Libertad", "Calle Reforma", "Calle de los Olivos",
          "Av. de la Industria"]
DESCRIPCIONES_BACHE = ["Hueco grande junto a la banqueta", "Se hunde el pavimento después de la lluvia",
                       "Los coches tienen que esquivarlo", "Está cerca de la esquina", "Lleva varias semanas así",
                       "Es peligroso para quien va en moto"]
DESCRIPCIONES_ENCHARCAMIENTO = ["Se acumula agua cada vez que llueve", "El agua no tiene por dónde salir",
                                "Casi no se puede pasar", "Se forma un charco grande en la esquina"]
TEXTOS_MOTIVO_OTRO = ["Es una propiedad privada.", "La ubicación no corresponde a una calle pública."]

# (valor, peso) para elegir al azar con random.choices
PESOS_TIPO_DANO = [("bache", 55), ("hundimiento", 18), ("grieta", 17), ("alcantarilla_sin_tapa", 10)]
PESOS_TAMANO = [("chico", 35), ("mediano", 40), ("grande", 25)]
PESOS_PROFUNDIDAD = [("baja", 40), ("media", 40), ("alta", 20)]
PESOS_NIVEL_AGUA = [("a_un_lado", 30), ("cubre_carril", 35), ("media_llanta", 22), ("intransitable", 13)]
PESOS_MOTIVO = [("duplicado", 40), ("no_es_via_publica", 20), ("otro", 20), ("fuera_del_municipio", 10),
                ("contenido_inapropiado", 10)]

# Camino que recorre un bache desde "recibido" hasta su estado final y cuánto tarda cada salto (min, max en horas)
CAMINO_BACHE = {
    "recibido": [],
    "validado": ["validado"],
    "en_reparacion": ["validado", "en_reparacion"],
    "reparado": ["validado", "en_reparacion", "reparado"],
    "rechazado": ["rechazado"],
}
RETRASO_HORAS = {"validado": (3, 72), "rechazado": (2, 48), "en_reparacion": (24, 240), "reparado": (48, 600)}
# Antigüedad mínima (días) para que un bache haya tenido tiempo de llegar a su estado final
MINIMO_DIAS_BACHE = {"recibido": 0, "rechazado": 0.5, "validado": 1, "en_reparacion": 4, "reparado": 8}
COMENTARIOS_BACHE = {
    "validado": [None, "Confirmado por el moderador", "Visto en sitio"],
    "en_reparacion": [None, "Cuadrilla asignada", "Programado para esta semana"],
    "reparado": [None, "Bache tapado", "Reparación terminada"],
}
COMENTARIO_VIGENCIA = "Venció la vigencia"
COMENTARIO_DESMENTIDOS = "Tres personas indicaron que ya no hay agua"


@dataclass
class _Lugar:
    colonia: Colonia
    lat: float
    lon: float
    calle: str
    hace: timedelta | None = None  # fijo solo en los puntos recurrentes (hace cuánto se reportó)


@dataclass
class _Contexto:
    rng: random.Random
    hoy: datetime
    tipos: dict[str, TipoDano]
    motivos: dict[str, MotivoRechazo]
    moderador: Usuario
    coordinador: Usuario
    ciudadano_demo: Usuario
    ficticios: list[Usuario]
    pesos_semana: list[float]

    @property
    def ciudadanos(self) -> list[Usuario]:
        return [*self.ficticios, self.ciudadano_demo]


def calcular_severidad(tipo_dano: str, tamano: str | None, profundidad: str | None) -> str:
    """Misma regla que el contrato (DISENO_TECNICO, sección 4): alcantarilla, tamaño grande o profundidad alta
    = alta; tamaño mediano = media; lo demás = baja."""
    if tipo_dano == "alcantarilla_sin_tapa" or tamano == "grande" or profundidad == "alta":
        return "alta"
    return "media" if tamano == "mediano" else "baja"


def _elegir(rng: random.Random, opciones: list[tuple[str, int]]) -> str:
    return rng.choices([valor for valor, _ in opciones], [peso for _, peso in opciones])[0]


def _desplazar(lat: float, lon: float, rumbo: float, metros: float) -> tuple[float, float]:
    """Punto a `metros` de distancia en la dirección `rumbo` (radianes). Aproximación plana: sobra para 1 km."""
    d_lat = metros * math.cos(rumbo) / METROS_POR_GRADO_LAT
    d_lon = metros * math.sin(rumbo) / (METROS_POR_GRADO_LAT * math.cos(math.radians(lat)))
    return lat + d_lat, lon + d_lon


def _cerca_de(rng: random.Random, lat: float, lon: float, minimo_m: float, maximo_m: float) -> tuple[float, float]:
    return _desplazar(lat, lon, rng.uniform(0, 2 * math.pi), rng.uniform(minimo_m, maximo_m))


def _hace_cuanto(ctx: _Contexto, minimo_dias: float = 0) -> timedelta:
    """Antigüedad al azar dentro de las 12 semanas; las semanas recientes pesan más (más volumen reciente)."""
    while True:
        semana = ctx.rng.choices(range(SEMANAS), ctx.pesos_semana)[0]
        dias = (semana + ctx.rng.random()) * 7
        if dias >= minimo_dias:
            return timedelta(days=dias)


def _despues(ctx: _Contexto, desde: datetime, min_horas: float, max_horas: float) -> datetime:
    """Instante entre min y max horas después de `desde`, sin pasar de "ahora": nada ficticio sucede en el futuro."""
    momento = desde + timedelta(hours=ctx.rng.uniform(min_horas, max_horas))
    limite = ctx.hoy - timedelta(minutes=5)
    if momento > limite:
        momento = desde + max(limite - desde, timedelta(0)) * ctx.rng.uniform(0.4, 0.95)
    return momento


def _autor(ctx: _Contexto) -> Usuario:
    """Casi todos los reportes son de cuentas ficticias; unos pocos, de la cuenta demo (para que "Mis reportes"
    no salga vacío al entrar con ella)."""
    if ctx.rng.random() < 0.03:
        return ctx.ciudadano_demo
    return ctx.rng.choice(ctx.ficticios)


def _cambio(
    reporte: Reporte, anterior: str | None, nuevo: str, actor: Usuario | None, cuando: datetime, comentario=None
) -> None:
    """Agrega al reporte una fila de historial con fecha explícita (registrar_cambio_estado usaría la hora actual).
    Antes valida el salto con la misma tabla que usa la aplicación."""
    if anterior is not None and not puede_pasar(reporte.categoria, anterior, nuevo):
        raise ErrorSemilla(f"La semilla armó un salto inválido en el historial: {anterior} -> {nuevo}")
    HistorialEstado(
        reporte=reporte, estado_anterior=anterior, estado_nuevo=nuevo,
        actor_id=actor.id if actor else None, comentario=comentario, creado_en=cuando,
    )


def _filas_confirmacion(
    usuarios: list[Usuario], tipo: str, momentos: list[datetime]
) -> list[tuple[int, str, datetime]]:
    return [(u.id, tipo, momento) for u, momento in zip(usuarios, sorted(momentos), strict=True)]


def _rechazo(ctx: _Contexto) -> tuple[MotivoRechazo, str | None, str]:
    """Motivo del catálogo, texto cuando el motivo lo pide y comentario público."""
    motivo = ctx.motivos[_elegir(ctx.rng, PESOS_MOTIVO)]
    texto = ctx.rng.choice(TEXTOS_MOTIVO_OTRO) if motivo.pide_explicacion else None
    return motivo, texto, f"Rechazado: {motivo.nombre.lower()}"


def _armar_bache(ctx: _Contexto, lugar: _Lugar, estado: str, antiguo: bool):
    """Devuelve (reporte con su historial, confirmaciones como tuplas usuario_id, tipo, fecha)."""
    rng = ctx.rng
    autor = _autor(ctx)
    tipo = _elegir(rng, PESOS_TIPO_DANO)
    tamano = profundidad = carril = senalizado = None
    if tipo == "alcantarilla_sin_tapa":
        senalizado = rng.random() < 0.4
    else:
        tamano, carril = _elegir(rng, PESOS_TAMANO), rng.choice(CARRILES)
        if tipo == "bache":  # hundimiento y grieta no piden profundidad (CONTRATO_API, sección 6.2)
            profundidad = _elegir(rng, PESOS_PROFUNDIDAD)

    hace = timedelta(days=rng.uniform(58, 80)) if antiguo else _hace_cuanto(ctx, MINIMO_DIAS_BACHE[estado])
    creado = ctx.hoy - hace
    reporte = Reporte(
        categoria="bache", tipo_dano_id=ctx.tipos[tipo].id, autor_id=autor.id, colonia_id=lugar.colonia.id,
        calle=lugar.calle, lat=lugar.lat, lon=lugar.lon,
        descripcion=rng.choice(DESCRIPCIONES_BACHE) if rng.random() < 0.4 else None,
        severidad=calcular_severidad(tipo, tamano, profundidad), tamano=tamano, profundidad=profundidad,
        carril=carril, senalizado=senalizado, estado=estado, creado_en=creado,
    )

    # Historial: el alta (actor = autor) y luego cada salto, con fechas crecientes
    _cambio(reporte, None, "recibido", autor, creado)
    anterior, momento = "recibido", creado
    for nuevo in CAMINO_BACHE[estado]:
        momento = _despues(ctx, momento, *RETRASO_HORAS[nuevo])
        if nuevo == "rechazado":
            motivo, texto, comentario = _rechazo(ctx)
            reporte.motivo_rechazo_id, reporte.motivo_texto = motivo.id, texto
            actor = ctx.moderador
        else:
            comentario = rng.choice(COMENTARIOS_BACHE[nuevo])
            actor = ctx.moderador if nuevo == "validado" else rng.choice([ctx.moderador, ctx.coordinador])
        if nuevo == "reparado":
            reporte.fecha_reparacion = a_hora_local(momento).date()
        _cambio(reporte, anterior, nuevo, actor, momento, comentario)
        anterior = nuevo

    # Confirmaciones ("yo también lo vi") en la mitad de los baches no rechazados
    confirmaciones = []
    if estado != "rechazado" and rng.random() < 0.5:
        votantes = rng.sample([u for u in ctx.ciudadanos if u.id != autor.id], rng.choice([1, 1, 2, 2, 3, 4, 5, 6]))
        momentos = [_despues(ctx, creado, 0.2, 144) for _ in votantes]
        confirmaciones = _filas_confirmacion(votantes, "confirma", momentos)
    reporte.confirmaciones = len(confirmaciones)
    return reporte, confirmaciones


def _armar_encharcamiento(ctx: _Contexto, lugar: _Lugar, estado: str, causa: str):
    """causa: cómo termina un encharcamiento que no está activo: "vigencia" (venció), "desmentidos" (tres personas
    dicen que ya no hay agua) o, solo en los rechazados, "directo" (el moderador lo rechaza estando activo)."""
    rng = ctx.rng
    autor = _autor(ctx)
    nivel = _elegir(rng, PESOS_NIVEL_AGUA)
    if estado == "activo":
        creado = ctx.hoy - timedelta(minutes=rng.uniform(25, 210))
    else:  # los cerrados tienen al menos 12 h, para que ya haya vencido su vigencia
        creado = ctx.hoy - (lugar.hace or _hace_cuanto(ctx, 0.5))

    # "Sigue ahí": cada una renueva la vigencia 6 h desde su momento (HU-03.2). El rechazo directo no las trae.
    n_sigue = 0 if causa == "directo" else rng.choices([0, 1, 2, 3], [50, 25, 15, 10])[0]
    if estado == "activo":
        n_sigue = min(n_sigue, 1)
    votantes = rng.sample([u for u in ctx.ciudadanos if u.id != autor.id], n_sigue + 3)
    momentos_sigue = [_despues(ctx, creado, 0.3, 4) for _ in range(n_sigue)]
    ultima = max([creado, *momentos_sigue])
    vigente_hasta = ultima + timedelta(hours=VIGENCIA_ENCHARCAMIENTO_HORAS)
    confirmaciones = _filas_confirmacion(votantes[:n_sigue], "sigue", momentos_sigue)

    reporte = Reporte(
        categoria="encharcamiento", autor_id=autor.id, colonia_id=lugar.colonia.id, calle=lugar.calle,
        lat=lugar.lat, lon=lugar.lon, nivel_agua=nivel, vigente_hasta=vigente_hasta, estado=estado,
        hay_riesgo=(rng.random() < 0.35) if nivel == "intransitable" else None,
        descripcion=rng.choice(DESCRIPCIONES_ENCHARCAMIENTO) if rng.random() < 0.4 else None,
        confirmaciones=n_sigue, creado_en=creado,
    )
    _cambio(reporte, None, "activo", autor, creado)
    if estado == "activo":
        return reporte, confirmaciones

    if causa == "desmentidos":
        # Tres personas distintas dicen "ya no hay agua" antes de que venza; la tercera cierra el reporte
        momentos = [ultima + timedelta(hours=rng.uniform(0.2, 1.5)) for _ in range(3)]
        confirmaciones += _filas_confirmacion(votantes[n_sigue:], "ya_no_hay", momentos)
        cierre, comentario = max(momentos) + timedelta(seconds=1), COMENTARIO_DESMENTIDOS
    else:
        cierre, comentario = vigente_hasta, COMENTARIO_VIGENCIA

    if estado == "historico":
        _cambio(reporte, "activo", "historico", None, cierre, comentario)  # actor None = sistema
    else:  # rechazado
        motivo, texto, comentario_rechazo = _rechazo(ctx)
        reporte.motivo_rechazo_id, reporte.motivo_texto = motivo.id, texto
        if causa == "directo":
            cuando = creado + timedelta(hours=rng.uniform(0.5, 4))
            _cambio(reporte, "activo", "rechazado", ctx.moderador, cuando, comentario_rechazo)
        else:  # venció y después el moderador lo rechazó
            _cambio(reporte, "activo", "historico", None, cierre, comentario)
            cuando = _despues(ctx, cierre, 1, 48)
            _cambio(reporte, "historico", "rechazado", ctx.moderador, cuando, comentario_rechazo)
    return reporte, confirmaciones


def _repartir(proporciones: list[tuple[str, int]], total: int) -> list[str]:
    """Lista de `total` estados según los porcentajes; el sobrante del redondeo se le da al estado más grande."""
    cantidades = {estado: round(total * porcentaje / 100) for estado, porcentaje in proporciones}
    mayor = max(cantidades, key=cantidades.get)
    cantidades[mayor] += total - sum(cantidades.values())
    return [estado for estado, cuantos in cantidades.items() for _ in range(cuantos)]


def _crear_ciudadanos_ficticios(db: Session, hoy: datetime) -> list[Usuario]:
    """30 cuentas ciudadanas ficticias que solo sirven de autoras y votantes. Su contraseña es aleatoria y se
    descarta al terminar: nadie la conoce, así que no se puede entrar con ellas."""
    correos = [f"ciudadano{i:02d}@{DOMINIO_FICTICIO}" for i in range(1, CIUDADANOS_FICTICIOS + 1)]
    cuentas = {u.correo: u for u in db.scalars(select(Usuario).where(Usuario.correo.in_(correos)))}
    hash_desconocido = None  # un solo hash para todas: bcrypt tarda ~0.2 s por cuenta
    alta = hoy - timedelta(days=SEMANAS * 7 + 1)
    for i, correo in enumerate(correos):
        if correo in cuentas:
            continue
        hash_desconocido = hash_desconocido or hash_password(secrets.token_urlsafe(32))
        cuentas[correo] = Usuario(
            nombre=f"{PRIMEROS_NOMBRES[i % 15]} {APELLIDOS[(i * 3 + i // 15) % len(APELLIDOS)]}",
            correo=correo, password_hash=hash_desconocido, rol="ciudadano", acepto_privacidad_en=alta, creado_en=alta,
        )
        db.add(cuentas[correo])
    db.flush()
    return [cuentas[correo] for correo in correos]


def _usuario_demo(db: Session, correo: str) -> Usuario:
    usuario = db.scalar(select(Usuario).where(func.lower(Usuario.correo) == normalizar_correo(correo)))
    if usuario is None:
        raise ErrorSemilla(f"Falta la cuenta de demostración {correo}: corre antes las cuentas demo (sembrar).")
    return usuario


def _lugares_de_baches(ctx: _Contexto, colonias: list[Colonia], pesos: list[float], total: int) -> list[_Lugar]:
    rng = ctx.rng
    lugares = []
    # Grupos de baches a lo largo de una calle, separados ~55 m (más que el radio de duplicado, 30 m)
    for _ in range(GRUPOS_DE_BACHES):
        colonia = rng.choices(colonias, pesos)[0]
        lat, lon = _cerca_de(rng, colonia.lat, colonia.lon, 100, 400)
        calle, rumbo = rng.choice(CALLES), rng.uniform(0, 2 * math.pi)
        for k in range(BACHES_POR_GRUPO):
            lat_k, lon_k = _desplazar(lat, lon, rumbo, k * 55 + rng.uniform(-4, 4))
            lugares.append(_Lugar(colonia, lat_k, lon_k, calle))
    while len(lugares) < total:
        colonia = rng.choices(colonias, pesos)[0]
        lat, lon = _cerca_de(rng, colonia.lat, colonia.lon, 100, 600)
        lugares.append(_Lugar(colonia, lat, lon, rng.choice(CALLES)))
    rng.shuffle(lugares)
    return lugares


def _lugares_de_encharcamientos(ctx: _Contexto, colonias: list[Colonia], pesos: list[float], total: int):
    """Los primeros son los puntos recurrentes (HU-03.4): cada punto se encharca en 4 a 6 días distintos y todos
    sus reportes quedan a menos de 20 m del punto, o sea a menos de 50 m entre sí."""
    rng = ctx.rng
    if len(colonias) >= len(REPORTES_POR_PUNTO):
        sedes = rng.sample(colonias, len(REPORTES_POR_PUNTO))
    else:
        sedes = rng.choices(colonias, k=len(REPORTES_POR_PUNTO))
    lugares = []
    for colonia, cuantos in zip(sedes, REPORTES_POR_PUNTO, strict=True):
        lat, lon = _cerca_de(rng, colonia.lat, colonia.lon, 100, 400)
        calle = rng.choice(CALLES)
        # Tramos de 4 días y cada reporte en un tramo distinto: entre dos reportes hay al menos 1.5 días,
        # así que nunca caen en el mismo día (y siempre dentro de las 12 semanas)
        for tramo in rng.sample(range(2, 80, 4), cuantos):
            lat_r, lon_r = _cerca_de(rng, lat, lon, 0, 20)
            lugares.append(_Lugar(colonia, lat_r, lon_r, calle, timedelta(days=tramo + rng.uniform(0, 2.5))))
    while len(lugares) < total:
        colonia = rng.choices(colonias, pesos)[0]
        lat, lon = _cerca_de(rng, colonia.lat, colonia.lon, 100, 600)
        lugares.append(_Lugar(colonia, lat, lon, rng.choice(CALLES)))
    return lugares


def cargar_reportes_demo(db: Session, hoy: datetime | None = None, semilla: int = SEMILLA_DEMO) -> int:
    """Inserta 500 reportes ficticios con historial coherente y confirmaciones. Devuelve cuántos agregó.

    Idempotente: si la tabla de reportes ya tiene filas no hace nada y devuelve 0 (no mezcla datos de demo con
    reportes reales). Necesita las colonias con coordenadas, los catálogos y las cuentas demo (corre antes
    sembrar() y cargar_colonias()). Hace flush pero no commit: lo hace quien llama.
    """
    if db.scalar(select(func.count()).select_from(Reporte)):
        return 0
    hoy = como_utc(hoy) if hoy else ahora_utc()
    rng = random.Random(semilla)

    colonias = sorted(
        db.scalars(select(Colonia).where(Colonia.activa, Colonia.lat.is_not(None), Colonia.lon.is_not(None))),
        key=lambda c: (c.sector_id, c.nombre),
    )
    tipos = {t.codigo: t for t in db.scalars(select(TipoDano))}
    motivos = {m.codigo: m for m in db.scalars(select(MotivoRechazo))}
    if not colonias:
        raise ErrorSemilla("No hay colonias con coordenadas: carga primero el catálogo (cargar_colonias).")
    if not {c for c, _ in PESOS_TIPO_DANO} <= tipos.keys() or not {c for c, _ in PESOS_MOTIVO} <= motivos.keys():
        raise ErrorSemilla("Faltan tipos de daño o motivos de rechazo: corre antes los catálogos (sembrar).")

    # Las semanas recientes pesan más (de 1.9 a 0.7) y con un poco de variación, para que no sea una curva perfecta
    pesos_semana = [(1.9 - 0.11 * i) * rng.uniform(0.8, 1.2) for i in range(SEMANAS)]
    ctx = _Contexto(
        rng=rng, hoy=hoy, tipos=tipos, motivos=motivos,
        moderador=_usuario_demo(db, CORREO_MODERADOR_DEMO), coordinador=_usuario_demo(db, CORREO_COORDINADOR_DEMO),
        ciudadano_demo=_usuario_demo(db, CORREO_CIUDADANO_DEMO),
        ficticios=_crear_ciudadanos_ficticios(db, hoy), pesos_semana=pesos_semana,
    )

    # Algunas colonias tienen más reportes que otras (el "top 10" del tablero necesita diferencias)
    posiciones = list(range(len(colonias)))
    rng.shuffle(posiciones)
    pesos_colonia = [1 / (posicion + 1) ** 0.7 for posicion in posiciones]

    n_encharcamientos = TOTAL_REPORTES * PORCENTAJE_ENCHARCAMIENTOS // 100
    n_baches = TOTAL_REPORTES - n_encharcamientos
    construidos = []  # (reporte, confirmaciones)

    # --- Baches ---
    estados = _repartir(PROPORCION_ESTADOS_BACHE, n_baches)
    rng.shuffle(estados)
    abiertos = [i for i, estado in enumerate(estados) if estado in ("recibido", "validado", "en_reparacion")]
    antiguos = set(rng.sample(abiertos, BACHES_ANTIGUOS))
    for i, lugar in enumerate(_lugares_de_baches(ctx, colonias, pesos_colonia, n_baches)):
        construidos.append(_armar_bache(ctx, lugar, estados[i], i in antiguos))

    # --- Encharcamientos: los puntos recurrentes son históricos; entre el resto hay activos y rechazados ---
    lugares = _lugares_de_encharcamientos(ctx, colonias, pesos_colonia, n_encharcamientos)
    recurrentes = sum(REPORTES_POR_PUNTO)
    resto = ["activo"] * ENCHARCAMIENTOS_ACTIVOS + ["rechazado"] * ENCHARCAMIENTOS_RECHAZADOS
    resto += ["historico"] * (n_encharcamientos - recurrentes - len(resto))
    rng.shuffle(resto)
    rechazados = 0
    for lugar, estado in zip(lugares, ["historico"] * recurrentes + resto, strict=True):
        if estado == "rechazado":  # la mitad se rechaza estando activo y la otra mitad después de vencer
            causa = "directo" if rechazados % 2 == 0 else "vigencia"
            rechazados += 1
        else:
            causa = "desmentidos" if rng.random() < 0.25 else "vigencia"
        construidos.append(_armar_encharcamiento(ctx, lugar, estado, causa))

    # Folios consecutivos por categoría y año, en orden de fecha (RN-03): el reporte más antiguo recibe el número 1
    construidos.sort(key=lambda par: par[0].creado_en)
    for reporte, _ in construidos:
        reporte.folio = generar_folio(db, prefijo_de(reporte.categoria), a_hora_local(reporte.creado_en).year)
    db.add_all(reporte for reporte, _ in construidos)  # el historial entra solo, por la relación
    db.flush()
    db.add_all(
        Confirmacion(reporte_id=reporte.id, usuario_id=usuario_id, tipo=tipo, creado_en=cuando)
        for reporte, filas in construidos
        for usuario_id, tipo, cuando in filas
    )
    db.flush()
    return len(construidos)


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


def sembrar_todo(db: Session, ruta_csv: Path | str | None = None, hoy: datetime | None = None) -> None:
    """Todo el flujo en orden: catálogos, cuentas demo, colonias y reportes demo. Cada paso hace su commit.

    Si falta el CSV de colonias, falla ahí (ErrorSemilla) con un mensaje claro y deja guardado lo anterior:
    el error no se oculta, pero tampoco se pierde el trabajo de los pasos que sí pudieron correr.
    """
    for nombre, agregados in sembrar(db).items():
        print(f"  {nombre}: {agregados} nuevos")

    agregadas = cargar_colonias(db, ruta_csv)
    db.commit()
    print(f"  colonias: {agregadas} nuevas")

    # Los reportes demo solo se cargan con la tabla vacía: así no se mezclan con reportes reales
    creados = cargar_reportes_demo(db, hoy=hoy)
    db.commit()
    if creados:
        print(f"  reportes de demostración: {creados} nuevos (más 30 cuentas ciudadanas ficticias)")
    else:
        print("  reportes de demostración: ya hay reportes en la base, no se cargó nada")


def main() -> None:
    with SessionLocal() as db:
        try:
            sembrar_todo(db)
        except ErrorSemilla as error:
            db.rollback()
            print(f"ERROR en la semilla: {error}", file=sys.stderr)
            raise SystemExit(1) from None


if __name__ == "__main__":
    main()
