"""Encharcamientos: alta, vigencia automática y respuestas «sigue ahí» / «ya no hay agua» (HU-03.1 a HU-03.3).

VIGENCIA SIN TAREAS PROGRAMADAS (HU-03.2): no hay un proceso que corra cada hora. En su lugar, cada endpoint
que lee o escribe encharcamientos llama primero a expirar_vencidos(db), que pasa a «historico» los activos
cuya vigencia ya terminó y lo anota en el historial como "sistema" (actor NULL). Ya lo llaman:
cercanos, alta de encharcamientos, confirmaciones y mis-reportes.

Para Carlos (consulta pública, detalle, zona, tablero): llama expirar_vencidos(db) al inicio de tu endpoint,
antes de leer. Los «historico» NO se borran: siguen contando en los indicadores (HU-03.2 CA3).
"""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errores import error_validacion
from app.core.reglas import DESMENTIDOS_PARA_CERRAR, VIGENCIA_ENCHARCAMIENTO_HORAS
from app.core.tiempo import a_hora_local, ahora_utc
from app.models import Confirmacion, Reporte, Usuario
from app.schemas.reportes import EncharcamientoEntrada, ReporteMio, a_reporte_mio
from app.services.cercanos import rechazar_si_hay_duplicados
from app.services.estados import registrar_cambio_estado, registrar_estado_inicial
from app.services.folios import generar_folio, prefijo_de
from app.services.validaciones import validar_colonia, validar_limite_horario, validar_municipio

VIGENCIA = timedelta(hours=VIGENCIA_ENCHARCAMIENTO_HORAS)
COMENTARIO_VENCIDO = f"Pasó a histórico: {VIGENCIA_ENCHARCAMIENTO_HORAS} horas sin confirmaciones de que sigue ahí"
COMENTARIO_DESMENTIDO = f"Pasó a histórico: {DESMENTIDOS_PARA_CERRAR} personas confirmaron que ya no hay agua"


def expirar_vencidos(db: Session, ahora: datetime | None = None) -> int:
    """Pasa a «historico» los encharcamientos activos con `vigente_hasta` vencido. Devuelve cuántos cambió.

    Hace commit si cambió alguno (se llama al INICIO del endpoint, cuando todavía no hay nada pendiente).
    `ahora` se inyecta en las pruebas para "adelantar el reloj" sin esperar 6 horas.
    """
    ahora = ahora or ahora_utc()
    vencidos = list(
        db.scalars(
            select(Reporte).where(
                Reporte.categoria == "encharcamiento", Reporte.estado == "activo", Reporte.vigente_hasta <= ahora
            )
        )
    )
    for reporte in vencidos:
        registrar_cambio_estado(db, reporte, "historico", actor=None, comentario=COMENTARIO_VENCIDO)
    if vencidos:
        db.commit()
    return len(vencidos)


def crear_encharcamiento(
    db: Session, autor: Usuario, datos: EncharcamientoEntrada, ahora: datetime | None = None
) -> ReporteMio:
    """Crea un encharcamiento ya publicado como «activo» (RN-06) con folio ENC-AAAA-NNNNNN y vigencia de 6 h."""
    ahora = ahora or ahora_utc()
    expirar_vencidos(db, ahora)  # para no tomar como duplicado uno que ya venció
    if datos.nivel_agua == "intransitable" and datos.hay_riesgo is None:
        raise error_validacion({"hay_riesgo": "Indica si hay vehículos varados o personas en riesgo"})
    validar_colonia(db, datos.colonia_id)
    validar_municipio(datos.lat, datos.lon)
    validar_limite_horario(db, autor, ahora)
    if not datos.forzar:
        rechazar_si_hay_duplicados(db, "encharcamiento", datos.lat, datos.lon, ahora)

    reporte = Reporte(
        categoria="encharcamiento",
        autor_id=autor.id,
        lat=datos.lat,
        lon=datos.lon,
        calle=datos.calle,
        colonia_id=datos.colonia_id,
        descripcion=datos.descripcion,
        nivel_agua=datos.nivel_agua,
        hay_riesgo=datos.hay_riesgo,
        vigente_hasta=ahora + VIGENCIA,
        estado="activo",
        confirmaciones=0,
        creado_en=ahora,
        folio=generar_folio(db, prefijo_de("encharcamiento"), a_hora_local(ahora).year),
    )
    db.add(reporte)
    registrar_estado_inicial(db, reporte, autor)
    db.commit()
    db.refresh(reporte)
    return a_reporte_mio(reporte, a_hora_local(ahora).date())


def aplicar_respuesta(db: Session, reporte: Reporte, tipo: str, ahora: datetime) -> None:
    """Efecto de una respuesta sobre un encharcamiento activo (la fila de Confirmacion ya está agregada).

    - «sigue»: la vigencia pasa a ser 6 h DESDE ESTE MOMENTO y suma 1 a `confirmaciones` (HU-03.2 CA2).
    - «ya_no_hay»: con el tercer desmentido de personas distintas pasa a «historico» (HU-03.3 CA3).
    No hace commit.
    """
    if tipo == "sigue":
        reporte.vigente_hasta = ahora + VIGENCIA
        reporte.confirmaciones = Reporte.confirmaciones + 1  # suma en SQL, a prueba de clics simultáneos
        db.flush()
    elif tipo == "ya_no_hay":
        db.flush()  # para que el conteo incluya la respuesta que se acaba de agregar
        desmentidos = db.scalar(
            select(func.count(func.distinct(Confirmacion.usuario_id))).where(
                Confirmacion.reporte_id == reporte.id, Confirmacion.tipo == "ya_no_hay"
            )
        )
        if desmentidos >= DESMENTIDOS_PARA_CERRAR:
            registrar_cambio_estado(db, reporte, "historico", actor=None, comentario=COMENTARIO_DESMENTIDO)
