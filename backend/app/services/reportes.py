"""Baches: alta con sus reglas por tipo de daño (HU-02.1 y HU-02.2) y "Mis reportes" (HU-02.5)."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.errores import ErrorApi, error_validacion
from app.core.paginacion import paginar
from app.core.reglas import TAM_PAGINA_MIS_REPORTES
from app.core.tiempo import a_hora_local, ahora_utc, hoy_local
from app.models import Reporte, TipoDano, Usuario
from app.schemas.reportes import BacheEdicion, BacheEntrada, ReporteMio, a_reporte_mio
from app.services.cercanos import cercanos_publicos, rechazar_si_hay_duplicados
from app.services.encharcamientos import expirar_vencidos
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
    if not datos.forzar:
        rechazar_si_hay_duplicados(db, "bache", datos.lat, datos.lon, ahora)

    reporte = Reporte(categoria="bache", autor_id=autor.id, estado="recibido", confirmaciones=0, creado_en=ahora)
    _aplicar_datos_de_bache(reporte, datos, tipo)
    reporte.folio = generar_folio(db, prefijo_de("bache"), a_hora_local(ahora).year)  # año en hora de Juárez
    db.add(reporte)
    registrar_estado_inicial(db, reporte, autor)
    db.commit()
    db.refresh(reporte)
    return a_reporte_mio(reporte, a_hora_local(ahora).date())


def cercanos_para_formulario(db: Session, categoria: str, lat: float, lon: float) -> list:
    """GET /api/reportes/cercanos: primero vence los encharcamientos caducados y luego busca (HU-02.3, HU-03.1 CA4)."""
    expirar_vencidos(db)
    return cercanos_publicos(db, categoria, lat, lon)


# --- Mis reportes (HU-02.5) -----------------------------------------------------------------------
def listar_mis_reportes(db: Session, autor: Usuario, pagina: int) -> dict:
    """Reportes de la persona (baches y encharcamientos), 10 por página, del más reciente al más antiguo."""
    consulta = (
        select(Reporte)
        .options(joinedload(Reporte.tipo_dano), joinedload(Reporte.colonia), joinedload(Reporte.motivo_rechazo))
        .where(Reporte.autor_id == autor.id)
        .order_by(Reporte.creado_en.desc(), Reporte.id.desc())
    )
    expirar_vencidos(db)  # así sus encharcamientos vencidos ya aparecen como «historico»
    resultado = paginar(db, consulta, pagina, TAM_PAGINA_MIS_REPORTES)
    hoy = hoy_local()
    resultado["items"] = [a_reporte_mio(r, hoy) for r in resultado["items"]]
    return resultado


def _propio_y_editable(db: Session, usuario: Usuario, reporte_id: int) -> Reporte:
    """Solo el autor y solo mientras el reporte siga en «recibido» (HU-02.5 CA3, RN-07).

    404 si no existe, 403 SIN_PERMISO si es de otra persona, 409 REPORTE_NO_EDITABLE si ya cambió de estado.
    Un encharcamiento nace «activo» (RN-06), así que nunca es editable.
    """
    reporte = db.get(Reporte, reporte_id)
    if reporte is None:
        raise ErrorApi(404, "NO_ENCONTRADO", "El reporte no existe")
    if reporte.autor_id != usuario.id:
        raise ErrorApi(403, "SIN_PERMISO", "Solo quien creó el reporte puede modificarlo")
    if reporte.estado != "recibido":
        raise ErrorApi(
            409, "REPORTE_NO_EDITABLE", "Este reporte ya fue revisado y no se puede modificar ni eliminar"
        )
    return reporte


def editar_bache(db: Session, usuario: Usuario, reporte_id: int, datos: BacheEdicion) -> ReporteMio:
    """Corrige un bache propio en «recibido» con las mismas validaciones del alta (sin buscar duplicados).

    El folio, el estado, las confirmaciones y `creado_en` no cambian; la severidad se vuelve a calcular.
    """
    reporte = _propio_y_editable(db, usuario, reporte_id)
    tipo = validar_bache(db, datos)
    _aplicar_datos_de_bache(reporte, datos, tipo)
    db.commit()
    db.refresh(reporte)
    return a_reporte_mio(reporte, hoy_local())


def eliminar_reporte(db: Session, usuario: Usuario, reporte_id: int) -> None:
    """Borra un reporte propio en «recibido». Su historial y sus confirmaciones se van con él por
    ON DELETE CASCADE (el trigger de PostgreSQL de la migración 0001 solo permite ese borrado en cascada).
    Un reporte que ya salió de «recibido» nunca se borra (RN-07): queda su historia."""
    reporte = _propio_y_editable(db, usuario, reporte_id)
    db.delete(reporte)
    db.commit()
