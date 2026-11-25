"""Tablero de indicadores del coordinador (HU-07.1).

TODAS las cifras salen de consulta_reportes(FiltroReportes(...)) (services/consulta.py), la misma función que usa
la consulta pública. Aquí solo se cuentan y agrupan sus resultados como subconsulta; los filtros no se repiten.
Así el tablero y la lista coinciden con los mismos filtros (HU-07.1 CA5).

Qué cuenta el tablero: todos los estados salvo «rechazado» (los históricos SÍ cuentan, HU-03.2 CA3).
Los rechazados se informan aparte, en `totales.rechazados`.

Rendimiento (RNF-06): cada indicador es UNA consulta, sin importar cuántos reportes haya. Donde el cálculo
depende del día en Ciudad Juárez (antigüedad) o de restar fechas y horas (tiempo de reparación), se traen solo
las columnas necesarias y se calcula en Python, porque SQLite (pruebas) y PostgreSQL restan fechas distinto.
"""

from dataclasses import replace
from datetime import date, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.errores import error_validacion
from app.core.reglas import (
    ESTADOS_BACHE,
    ESTADOS_ENCHARCAMIENTO,
    TABLERO_MAS_LONGEVOS,
    TABLERO_SEMANAS,
    TABLERO_TOP_COLONIAS,
)
from app.core.tiempo import a_hora_local, como_utc, hoy_local
from app.models import Colonia, HistorialEstado, Reporte, Sector
from app.schemas.reportes import ESTADOS_BACHE_ABIERTOS, antiguedad_dias
from app.services.consulta import FiltroReportes, consulta_reportes, inicio_del_dia_utc
from app.services.encharcamientos import expirar_vencidos

# (categoria, estado) que se cuentan, en el orden en que se muestran. Sin «rechazado».
ESTADOS_POR_CATEGORIA = [("bache", e) for e in ESTADOS_BACHE if e != "rechazado"] + [
    ("encharcamiento", e) for e in ESTADOS_ENCHARCAMIENTO if e != "rechazado"
]
ESTADOS_TABLERO = tuple(estado for _categoria, estado in ESTADOS_POR_CATEGORIA)
SEGUNDOS_POR_DIA = 86400


def _sub(filtro: FiltroReportes):
    """Resultado de la consulta única como subconsulta, sin orden (no hace falta para contar)."""
    return consulta_reportes(filtro).order_by(None).subquery()


def _colonia(colonia_id: int, nombre: str) -> dict:
    return {"id": colonia_id, "nombre": nombre}


def _totales(db: Session, base: FiltroReportes) -> dict:
    sub = _sub(base)
    filas = db.execute(select(sub.c.categoria, sub.c.estado, func.count()).group_by(sub.c.categoria, sub.c.estado))
    conteo = {(categoria, estado): total for categoria, estado, total in filas}
    por_estado = [{"categoria": c, "estado": e, "total": conteo.get((c, e), 0)} for c, e in ESTADOS_POR_CATEGORIA]
    # Los rechazados se cuentan con la misma función, pidiéndolos explícitamente
    rechazados = _sub(replace(base, estados=("rechazado",), incluir_rechazados=True))
    return {
        "total": sum(conteo.values()),
        "bache": sum(t for (c, _e), t in conteo.items() if c == "bache"),
        "encharcamiento": sum(t for (c, _e), t in conteo.items() if c == "encharcamiento"),
        "por_estado": por_estado,
        "rechazados": db.scalar(select(func.count()).select_from(rechazados)),
    }


def _top_colonias(db: Session, abiertos: FiltroReportes) -> list[dict]:
    """Colonias con más baches abiertos; empate: por nombre (alfabético) y luego por id."""
    sub = _sub(abiertos)
    total = func.count().label("abiertos")
    consulta = (
        select(Colonia.id, Colonia.nombre, total)
        .join(sub, sub.c.colonia_id == Colonia.id)
        .group_by(Colonia.id, Colonia.nombre)
        .order_by(total.desc(), Colonia.nombre, Colonia.id)
        .limit(TABLERO_TOP_COLONIAS)
    )
    return [{"colonia": _colonia(i, n), "abiertos": a} for i, n, a in db.execute(consulta)]


def _tiempo_reparacion(db: Session, base: FiltroReportes) -> tuple[float | None, int]:
    """Promedio de días entre el cambio a «validado» y el cambio a «reparado», leído del historial."""
    sub = _sub(replace(base, categoria="bache", estados=("reparado",)))
    validado = (
        select(HistorialEstado.reporte_id, func.min(HistorialEstado.creado_en).label("en"))
        .where(HistorialEstado.estado_nuevo == "validado")
        .group_by(HistorialEstado.reporte_id)
        .subquery()
    )
    reparado = (
        select(HistorialEstado.reporte_id, func.max(HistorialEstado.creado_en).label("en"))
        .where(HistorialEstado.estado_nuevo == "reparado")
        .group_by(HistorialEstado.reporte_id)
        .subquery()
    )
    filas = db.execute(
        select(validado.c.en, reparado.c.en)
        .select_from(sub)
        .join(validado, validado.c.reporte_id == sub.c.id)
        .join(reparado, reparado.c.reporte_id == sub.c.id)
    ).all()
    if not filas:
        return None, 0
    dias = [(como_utc(fin) - como_utc(inicio)).total_seconds() / SEGUNDOS_POR_DIA for inicio, fin in filas]
    return round(sum(dias) / len(dias), 1), len(dias)


def _por_semana(db: Session, base: FiltroReportes, hoy: date) -> list[dict]:
    """Reportes creados en cada una de las últimas 12 semanas (lunes a domingo, hora de Juárez), con ceros.

    La serie termina en la semana de `hasta` (o en la actual si no se pidió) y cuenta con el filtro completo:
    una semana fuera de `desde`/`hasta` queda en 0.
    """
    fin = base.hasta or hoy
    ultimo_lunes = fin - timedelta(days=fin.weekday())
    lunes = [ultimo_lunes - timedelta(weeks=i) for i in range(TABLERO_SEMANAS - 1, -1, -1)]
    limites = [inicio_del_dia_utc(d) for d in lunes]
    sub = _sub(base)
    # Número de semana (0 a 11) calculado en SQL: la última semana cuyo inicio ya pasó
    semana = case(*[(sub.c.creado_en >= limites[i], i) for i in range(TABLERO_SEMANAS - 1, -1, -1)], else_=-1)
    filas = db.execute(
        select(semana.label("semana"), func.count())
        .where(sub.c.creado_en >= limites[0], sub.c.creado_en < inicio_del_dia_utc(ultimo_lunes + timedelta(days=7)))
        .group_by("semana")
    )
    conteo = dict(filas.all())
    return [{"inicio": d, "total": conteo.get(i, 0)} for i, d in enumerate(lunes)]


def _mas_longevos(db: Session, abiertos: FiltroReportes, hoy: date) -> list[dict]:
    consulta = (
        consulta_reportes(abiertos)
        .order_by(None)
        .order_by(Reporte.creado_en, Reporte.id)
        .options(joinedload(Reporte.colonia))
        .limit(TABLERO_MAS_LONGEVOS)
    )
    return [
        {
            "id": r.id,
            "folio": r.folio,
            "calle": r.calle,
            "colonia": _colonia(r.colonia.id, r.colonia.nombre),
            "estado": r.estado,
            "antiguedad_dias": antiguedad_dias(r, hoy),
        }
        for r in db.scalars(consulta)
    ]


def _longevidad_por_colonia(db: Session, abiertos: FiltroReportes, hoy: date) -> list[dict]:
    """Antigüedad promedio (RN-10) de los baches abiertos de cada colonia; de la más alta a la más baja."""
    sub = _sub(abiertos)
    filas = db.execute(select(Colonia.id, Colonia.nombre, sub.c.creado_en).join(sub, sub.c.colonia_id == Colonia.id))
    por_colonia: dict[tuple[int, str], list[int]] = {}
    for colonia_id, nombre, creado_en in filas:
        dias = max((hoy - a_hora_local(creado_en).date()).days, 0)
        por_colonia.setdefault((colonia_id, nombre), []).append(dias)
    resultado = [
        {"colonia": _colonia(i, n), "abiertos": len(d), "promedio_dias": round(sum(d) / len(d), 1)}
        for (i, n), d in por_colonia.items()
    ]
    return sorted(resultado, key=lambda x: (-x["promedio_dias"], x["colonia"]["nombre"], x["colonia"]["id"]))


def obtener_tablero(db: Session, desde: date | None, hasta: date | None, sector_id: int | None) -> dict:
    """GET /api/tablero: valida el filtro, vence encharcamientos y arma todos los indicadores."""
    if desde and hasta and desde > hasta:
        raise error_validacion({"hasta": "La fecha final no puede ser anterior a la inicial"})
    if sector_id is not None and db.get(Sector, sector_id) is None:
        raise error_validacion({"sector_id": "El sector no existe"})

    expirar_vencidos(db)  # los encharcamientos vencidos pasan a «historico» antes de contar
    hoy = hoy_local()
    base = FiltroReportes(estados=ESTADOS_TABLERO, sector_id=sector_id, desde=desde, hasta=hasta)
    abiertos = replace(base, categoria="bache", estados=ESTADOS_BACHE_ABIERTOS)
    promedio, medidos = _tiempo_reparacion(db, base)
    return {
        "filtro": {"desde": desde, "hasta": hasta, "sector_id": sector_id},
        "totales": _totales(db, base),
        "top_colonias": _top_colonias(db, abiertos),
        "tiempo_promedio_reparacion_dias": promedio,
        "reparados_medidos": medidos,
        "por_semana": _por_semana(db, base, hoy),
        "mas_longevos": _mas_longevos(db, abiertos, hoy),
        "longevidad_por_colonia": _longevidad_por_colonia(db, abiertos, hoy),
    }
