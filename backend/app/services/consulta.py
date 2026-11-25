"""Consulta pública de reportes con filtros, búsqueda y paginación (HU-04.1 y HU-04.2).

UNA SOLA FUNCIÓN DE FILTRADO: consulta_reportes(filtro) arma el SELECT de reportes. La usan la consulta pública
(GET /api/reportes) y debe usarla también el tablero (C10), para que los números del tablero coincidan con lo
que la persona ve en la lista con los mismos filtros (HU-07.1 CA5). Ejemplo para el tablero:

    from sqlalchemy import func, select
    from app.services.consulta import FiltroReportes, consulta_reportes

    filtro = FiltroReportes(estados=ESTADOS_BACHE_ABIERTOS, sector_id=3, desde=date(2026, 9, 1))
    sub = consulta_reportes(filtro).order_by(None).subquery()
    total = db.scalar(select(func.count()).select_from(sub))
"""

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.errores import error_validacion
from app.core.paginacion import paginar
from app.core.tiempo import ZONA_JUAREZ, hoy_local
from app.models import Colonia, Reporte, Usuario
from app.schemas.reportes import ESTADOS_BACHE_ABIERTOS, a_reporte_publico
from app.services.encharcamientos import expirar_vencidos

# Roles que pueden ver los reportes rechazados (filtrando estado=rechazado). El público nunca los ve (HU-04.1 CA4).
ROLES_VEN_RECHAZADOS = ("moderador", "coordinador")


@dataclass
class FiltroReportes:
    """Filtros de la consulta. Todo lo que queda en None no filtra.

    - estados: None = solo "activos" (baches abiertos y encharcamientos activos); una tupla = esos estados.
    - desde / hasta: días del calendario de Ciudad Juárez, ambos incluidos.
    - q: texto que se busca en la calle o en el folio, sin distinguir mayúsculas.
    - incluir_rechazados: False = los rechazados se quitan SIEMPRE, aunque se pidan en `estados`.
    - sector_id: lo usa el tablero; la consulta pública todavía no lo expone.
    """

    categoria: str | None = None
    estados: tuple[str, ...] | None = None
    colonia_id: int | None = None
    sector_id: int | None = None
    severidad: str | None = None
    desde: date | None = None
    hasta: date | None = None
    q: str | None = None
    incluir_rechazados: bool = False


def inicio_del_dia_utc(dia: date) -> datetime:
    """00:00 de ese día en Ciudad Juárez, convertido a UTC (la base guarda en UTC, RN-02)."""
    return datetime.combine(dia, time.min, tzinfo=ZONA_JUAREZ).astimezone(UTC)


def consulta_reportes(filtro: FiltroReportes) -> Select:
    """SELECT de reportes que cumplen el filtro, del más reciente al más antiguo (creado_en desc, id desc)."""
    condiciones = []

    if filtro.estados is None:
        # "Activos": lo que todavía afecta la calle
        condiciones.append(
            or_(
                and_(Reporte.categoria == "bache", Reporte.estado.in_(ESTADOS_BACHE_ABIERTOS)),
                and_(Reporte.categoria == "encharcamiento", Reporte.estado == "activo"),
            )
        )
    else:
        condiciones.append(Reporte.estado.in_(filtro.estados))
    if not filtro.incluir_rechazados:
        condiciones.append(Reporte.estado != "rechazado")

    if filtro.categoria:
        condiciones.append(Reporte.categoria == filtro.categoria)
    if filtro.colonia_id is not None:
        condiciones.append(Reporte.colonia_id == filtro.colonia_id)
    if filtro.sector_id is not None:
        condiciones.append(Reporte.colonia_id.in_(select(Colonia.id).where(Colonia.sector_id == filtro.sector_id)))
    if filtro.severidad:
        condiciones.append(Reporte.severidad == filtro.severidad)
    if filtro.desde:
        condiciones.append(Reporte.creado_en >= inicio_del_dia_utc(filtro.desde))
    if filtro.hasta:
        # Hasta el final del día: menor que las 00:00 del día siguiente
        condiciones.append(Reporte.creado_en < inicio_del_dia_utc(filtro.hasta + timedelta(days=1)))
    texto = (filtro.q or "").strip()
    if texto:
        # autoescape: un "%" o "_" escrito por la persona se busca tal cual, no como comodín
        condiciones.append(
            or_(Reporte.calle.icontains(texto, autoescape=True), Reporte.folio.icontains(texto, autoescape=True))
        )

    return select(Reporte).where(*condiciones).order_by(Reporte.creado_en.desc(), Reporte.id.desc())


def puede_ver_rechazados(usuario: Usuario | None) -> bool:
    return usuario is not None and usuario.rol in ROLES_VEN_RECHAZADOS


def listar_publicos(db: Session, usuario: Usuario | None, filtro: FiltroReportes, pagina: int, tam: int) -> dict:
    """GET /api/reportes: valida el rango de fechas, vence encharcamientos y devuelve una página de ReportePublico."""
    if filtro.desde and filtro.hasta and filtro.desde > filtro.hasta:
        raise error_validacion({"hasta": "La fecha final no puede ser anterior a la inicial"})
    # Lo decide el servidor según el rol, nunca un parámetro de la petición
    filtro = replace(filtro, incluir_rechazados=puede_ver_rechazados(usuario))

    expirar_vencidos(db)  # los encharcamientos vencidos pasan a «historico» antes de leer
    consulta = consulta_reportes(filtro).options(joinedload(Reporte.tipo_dano), joinedload(Reporte.colonia))
    resultado = paginar(db, consulta, pagina, tam)
    hoy = hoy_local()
    resultado["items"] = [a_reporte_publico(r, hoy) for r in resultado["items"]]
    return resultado
