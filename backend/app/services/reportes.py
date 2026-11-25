"""Baches: alta con sus reglas por tipo de daño (HU-02.1 y HU-02.2)."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errores import error_validacion
from app.core.tiempo import a_hora_local, ahora_utc
from app.models import Reporte, TipoDano, Usuario
from app.schemas.reportes import BacheEdicion, BacheEntrada, ReporteMio, a_reporte_mio
from app.services.estados import registrar_estado_inicial
from app.services.folios import generar_folio, prefijo_de
from app.services.validaciones import validar_colonia, validar_limite_horario, validar_municipio

# Campos que exige cada tipo de daño (HU-02.2). Un tipo nuevo que agregue el coordinador pide tamaño y carril.
CAMPOS_EXIGIDOS = {
    "bache": ("tamano", "profundidad", "carril"),
    "hundimiento": ("tamano", "carril"),
    "grieta": ("tamano", "carril"),
    "alcantarilla_sin_tapa": ("senalizado",),
}
CAMPOS_EXIGIDOS_OTRO_TIPO = ("tamano", "carril")

MENSAJES_CAMPO = {
    "tamano": "Indica el tamaño aproximado",
    "profundidad": "Indica la profundidad",
    "carril": "Indica en qué carril está",
    "senalizado": "Indica si la alcantarilla está señalizada",
}


def calcular_severidad(tipo_codigo: str, tamano: str | None, profundidad: str | None) -> str:
    """Severidad que calcula el servidor (DISENO_TECNICO, sección 4); la persona nunca la elige.

    alcantarilla sin tapa = alta; tamaño grande o profundidad alta = alta; tamaño mediano = media; resto = baja.
    """
    if tipo_codigo == "alcantarilla_sin_tapa":
        return "alta"
    if tamano == "grande" or profundidad == "alta":
        return "alta"
    if tamano == "mediano":
        return "media"
    return "baja"


def _validar_tipo_y_campos(db: Session, datos: BacheEdicion) -> TipoDano:
    """El tipo debe existir y estar activo; luego se exigen los campos de ese tipo (422 con un mensaje por campo)."""
    tipo = db.scalar(select(TipoDano).where(TipoDano.codigo == datos.tipo_dano_codigo, TipoDano.activo.is_(True)))
    if tipo is None:
        raise error_validacion({"tipo_dano_codigo": "Elige un tipo de daño de la lista"})
    exigidos = CAMPOS_EXIGIDOS.get(tipo.codigo, CAMPOS_EXIGIDOS_OTRO_TIPO)
    faltantes = {campo: MENSAJES_CAMPO[campo] for campo in exigidos if getattr(datos, campo) is None}
    if faltantes:
        raise error_validacion(faltantes)
    return tipo


def _aplicar_datos_de_bache(reporte: Reporte, datos: BacheEdicion, tipo: TipoDano) -> None:
    """Copia al modelo los campos del formulario (alta y edición usan la misma función)."""
    reporte.tipo_dano_id = tipo.id
    reporte.lat = datos.lat
    reporte.lon = datos.lon
    reporte.calle = datos.calle
    reporte.colonia_id = datos.colonia_id
    reporte.descripcion = datos.descripcion
    reporte.tamano = datos.tamano
    reporte.profundidad = datos.profundidad
    reporte.carril = datos.carril
    # "¿Está señalizada?" solo tiene sentido en una alcantarilla sin tapa
    reporte.senalizado = datos.senalizado if tipo.codigo == "alcantarilla_sin_tapa" else None
    reporte.severidad = calcular_severidad(tipo.codigo, datos.tamano, datos.profundidad)


def validar_bache(db: Session, datos: BacheEdicion) -> TipoDano:
    """Validaciones de negocio de un bache (alta y edición): tipo y sus campos, colonia y municipio."""
    tipo = _validar_tipo_y_campos(db, datos)
    validar_colonia(db, datos.colonia_id)
    validar_municipio(datos.lat, datos.lon)
    return tipo


def crear_bache(db: Session, autor: Usuario, datos: BacheEntrada, ahora: datetime | None = None) -> ReporteMio:
    """Crea un bache en «recibido» con folio BCH-AAAA-NNNNNN y su primera fila del historial (HU-02.1 CA3).

    `ahora` se puede inyectar en las pruebas; en la API siempre es la hora del servidor (la entrada no trae fecha).
    """
    ahora = ahora or ahora_utc()
    tipo = validar_bache(db, datos)
    validar_limite_horario(db, autor, ahora)

    reporte = Reporte(categoria="bache", autor_id=autor.id, estado="recibido", confirmaciones=0, creado_en=ahora)
    _aplicar_datos_de_bache(reporte, datos, tipo)
    reporte.folio = generar_folio(db, prefijo_de("bache"), a_hora_local(ahora).year)  # año en hora de Juárez
    db.add(reporte)
    registrar_estado_inicial(db, reporte, autor)
    db.commit()
    db.refresh(reporte)
    return a_reporte_mio(reporte, a_hora_local(ahora).date())
