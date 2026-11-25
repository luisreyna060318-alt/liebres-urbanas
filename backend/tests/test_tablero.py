"""Tablero de indicadores (HU-07.1): cifras exactas, coincidencia con la consulta, roles, 422 y privacidad."""

from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.core.tiempo import ZONA_JUAREZ, ahora_utc, hoy_local
from app.models import Colonia, HistorialEstado, Reporte, Sector
from app.services.consulta import FiltroReportes, consulta_reportes
from app.services.estados import registrar_cambio_estado
from tests.conftest import LLAVES_PROHIBIDAS, encabezado_de, llaves_de


def local(dia: date, hora: int = 12, minuto: int = 0) -> datetime:
    """Una hora de Ciudad Juárez convertida a UTC (así se guarda en la base)."""
    return datetime.combine(dia, time(hora, minuto), tzinfo=ZONA_JUAREZ).astimezone(UTC)


@pytest.fixture()
def datos(db: Session, catalogo, ciudadano):
    """Fábrica de reportes insertados directo en la base. Hay un segundo sector («Sur») con su colonia."""
    sur = Sector(nombre="Sur")
    db.add(sur)
    db.flush()
    lejana = Colonia(nombre="Colonia Lejana", sector_id=sur.id)
    db.add(lejana)
    db.commit()
    contador = {"n": 0}

    def _crear(categoria="bache", estado=None, colonia=None, creado_en=None, guardar=True, **extra):
        contador["n"] += 1
        n = contador["n"]
        comunes = dict(
            autor_id=ciudadano.id, colonia_id=(colonia or catalogo["colonia"]).id, calle=f"Calle Ficticia {n}",
            lat=31.7, lon=-106.43, creado_en=creado_en or local(hoy_local() - timedelta(days=1)),
        )
        if categoria == "bache":
            estado = estado or "recibido"
            reporte = Reporte(
                folio=f"BCH-2026-{n:06d}", categoria="bache", tipo_dano_id=catalogo["tipos"]["bache"].id,
                severidad="baja", tamano="chico", profundidad="baja", carril="orilla", estado=estado,
                fecha_reparacion=extra.pop("fecha_reparacion", hoy_local()) if estado == "reparado" else None,
                **comunes, **extra,
            )
        else:
            reporte = Reporte(
                folio=f"ENC-2026-{n:06d}", categoria="encharcamiento", nivel_agua="cubre_carril",
                vigente_hasta=extra.pop("vigente_hasta", ahora_utc() + timedelta(hours=6)),
                estado=estado or "activo", **comunes, **extra,
            )
        db.add(reporte)
        if guardar:
            db.commit()
        return reporte

    _crear.sur = sur
    _crear.lejana = lejana
    return _crear


def tablero(client, coordinador, **params):
    r = client.get("/api/tablero", params=params, headers=encabezado_de(coordinador))
    assert r.status_code == 200, r.text
    return r.json()


def por_estado(cuerpo) -> dict[tuple[str, str], int]:
    return {(f["categoria"], f["estado"]): f["total"] for f in cuerpo["totales"]["por_estado"]}


# --- 1. Totales por tipo y estado ----------------------------------------------------------------
def test_totales_exactos_historico_cuenta_y_rechazados_aparte(client, datos, coordinador):
    for estado in ("recibido", "recibido", "validado", "en_reparacion", "reparado", "rechazado"):
        datos("bache", estado)
    for estado in ("activo", "historico", "historico", "rechazado"):
        datos("encharcamiento", estado)
    # Activo pero ya vencido: expirar_vencidos lo pasa a histórico y sigue contando (HU-03.2 CA3)
    datos("encharcamiento", vigente_hasta=ahora_utc() - timedelta(minutes=1))

    cuerpo = tablero(client, coordinador)
    totales = cuerpo["totales"]
    assert (totales["total"], totales["bache"], totales["encharcamiento"], totales["rechazados"]) == (9, 5, 4, 2)
    assert por_estado(cuerpo) == {
        ("bache", "recibido"): 2, ("bache", "validado"): 1, ("bache", "en_reparacion"): 1, ("bache", "reparado"): 1,
        ("encharcamiento", "activo"): 1, ("encharcamiento", "historico"): 3,
    }


def test_sin_reportes_todo_en_cero(client, catalogo, coordinador):
    cuerpo = tablero(client, coordinador)
    assert cuerpo["totales"]["total"] == 0 and set(por_estado(cuerpo).values()) == {0}
    assert cuerpo["top_colonias"] == [] and cuerpo["mas_longevos"] == [] and cuerpo["longevidad_por_colonia"] == []
    assert cuerpo["tiempo_promedio_reparacion_dias"] is None and cuerpo["reparados_medidos"] == 0
    assert len(cuerpo["por_semana"]) == 12 and all(s["total"] == 0 for s in cuerpo["por_semana"])


# --- CA5: el tablero coincide con la consulta con los mismos filtros ------------------------------
@pytest.mark.parametrize("filtro", ["ninguno", "fechas", "sector", "fechas_y_sector"])
def test_coincide_con_consulta_reportes(client, db, datos, coordinador, filtro):
    hoy = hoy_local()
    estados_bache = ("recibido", "validado", "en_reparacion", "reparado", "rechazado")
    estados_ench = ("activo", "historico", "rechazado")
    for i in range(30):
        colonia = datos.lejana if i % 3 == 0 else None
        creado = local(hoy - timedelta(days=i * 2), hora=i % 24)
        if i % 4 == 3:
            datos("encharcamiento", estados_ench[i % 3], colonia=colonia, creado_en=creado)
        else:
            datos("bache", estados_bache[i % 5], colonia=colonia, creado_en=creado)

    params = {}
    if "fechas" in filtro:
        params.update(desde=(hoy - timedelta(days=30)).isoformat(), hasta=(hoy - timedelta(days=6)).isoformat())
    if "sector" in filtro:
        params["sector_id"] = datos.sur.id
    cuerpo = tablero(client, coordinador, **params)

    desde = date.fromisoformat(params["desde"]) if "desde" in params else None
    hasta = date.fromisoformat(params["hasta"]) if "hasta" in params else None
    for (categoria, estado), total in por_estado(cuerpo).items():
        f = FiltroReportes(categoria=categoria, estados=(estado,), desde=desde, hasta=hasta,
                           sector_id=params.get("sector_id"))
        esperado = db.scalar(select(func.count()).select_from(consulta_reportes(f).order_by(None).subquery()))
        assert total == esperado, (categoria, estado)
        if "sector_id" not in params:
            # La lista pública (GET /api/reportes) con los mismos filtros da el mismo total
            lista = client.get("/api/reportes", params={"categoria": categoria, "estado": estado, **params})
            assert lista.json()["total"] == total, (categoria, estado)
    assert cuerpo["totales"]["total"] > 0


# --- 2. Top 10 colonias con más baches abiertos ---------------------------------------------------
def test_top_10_colonias_solo_abiertos_y_desempate_alfabetico(client, db, datos, catalogo, coordinador):
    colonias = [Colonia(nombre=f"Colonia {letra}", sector_id=catalogo["sector"].id) for letra in "LKJIHGFEDCBA"]
    db.add_all(colonias)
    db.commit()
    # Colonia L: 5 abiertos; K: 4; J e I empatan con 3 (gana I por nombre); el resto 1
    cantidades = [5, 4, 3, 3, 1, 1, 1, 1, 1, 1, 1, 1]
    estados = ("recibido", "validado", "en_reparacion")
    for colonia, cantidad in zip(colonias, cantidades, strict=True):
        for i in range(cantidad):
            datos("bache", estados[i % 3], colonia=colonia, guardar=False)
    # Lo que NO cuenta: reparados, rechazados y encharcamientos
    for _ in range(6):
        datos("bache", "reparado", colonia=colonias[-1], guardar=False)
        datos("bache", "rechazado", colonia=colonias[-1], guardar=False)
        datos("encharcamiento", colonia=colonias[-1], guardar=False)
    db.commit()

    top = tablero(client, coordinador)["top_colonias"]
    assert [(t["colonia"]["nombre"], t["abiertos"]) for t in top] == [
        ("Colonia L", 5), ("Colonia K", 4), ("Colonia I", 3), ("Colonia J", 3),
        ("Colonia A", 1), ("Colonia B", 1), ("Colonia C", 1), ("Colonia D", 1), ("Colonia E", 1), ("Colonia F", 1),
    ]


# --- 3. Tiempo promedio de reparación con el historial real ---------------------------------------
@pytest.fixture()
def reloj(db):
    """Fija la fecha y hora de las filas nuevas del historial (registrar_cambio_estado usa la hora actual)."""
    estado = {"ahora": None}

    def _poner_hora(_mapper, _conexion, fila):
        if estado["ahora"] is not None:
            fila.creado_en = estado["ahora"]

    event.listen(HistorialEstado, "before_insert", _poner_hora)
    yield estado
    event.remove(HistorialEstado, "before_insert", _poner_hora)


def reparar(db, reloj, reporte, validado_en, reparado_en, moderador):
    """Recorre recibido → validado → en_reparacion → reparado con registrar_cambio_estado y horas controladas."""
    reloj["ahora"] = validado_en
    registrar_cambio_estado(db, reporte, "validado", actor=moderador)
    reloj["ahora"] = validado_en + timedelta(hours=1)
    registrar_cambio_estado(db, reporte, "en_reparacion", actor=moderador)
    reloj["ahora"] = reparado_en
    fecha = reparado_en.astimezone(ZONA_JUAREZ).date()
    registrar_cambio_estado(db, reporte, "reparado", actor=moderador, fecha_reparacion=fecha)
    db.commit()


def test_tiempo_promedio_de_validado_a_reparado(client, db, datos, coordinador, moderador, reloj):
    hoy = hoy_local()
    inicio = local(hoy - timedelta(days=20), hora=9)
    a = datos("bache", creado_en=inicio)
    b = datos("bache", creado_en=inicio)
    reparar(db, reloj, a, inicio + timedelta(days=1), inicio + timedelta(days=3), moderador)  # 2 días
    reparar(db, reloj, b, inicio + timedelta(days=1), inicio + timedelta(days=6), moderador)  # 5 días
    # Validado pero aún sin reparar: no entra en el promedio
    c = datos("bache", creado_en=inicio)
    reloj["ahora"] = inicio + timedelta(days=1)
    registrar_cambio_estado(db, c, "validado", actor=moderador)
    db.commit()

    cuerpo = tablero(client, coordinador)
    assert cuerpo["tiempo_promedio_reparacion_dias"] == 3.5 and cuerpo["reparados_medidos"] == 2

    # El filtro también aplica: con un rango que deja fuera a los dos reparados no hay datos (null)
    vacio = tablero(client, coordinador, desde=(hoy - timedelta(days=5)).isoformat())
    assert vacio["tiempo_promedio_reparacion_dias"] is None and vacio["reparados_medidos"] == 0


# --- 4. Reportes por semana ----------------------------------------------------------------------
def test_doce_semanas_con_ceros_y_lunes_de_juarez(client, datos, coordinador):
    hoy = hoy_local()
    lunes = hoy - timedelta(days=hoy.weekday())
    # Domingo 23:30 en Juárez (ya es lunes en UTC) cuenta en la semana ANTERIOR; lunes 00:10 en la actual
    datos("bache", creado_en=local(lunes - timedelta(days=1), 23, 30))
    datos("encharcamiento", "historico", creado_en=local(lunes, 0, 10))
    datos("bache", creado_en=local(lunes - timedelta(weeks=5), 8))
    datos("bache", creado_en=local(lunes - timedelta(weeks=5) + timedelta(days=6), 20))
    datos("bache", creado_en=local(lunes - timedelta(weeks=12), 8))  # semana 13: fuera de la serie
    datos("bache", "rechazado", creado_en=local(lunes, 9))  # rechazado: no cuenta

    semanas = tablero(client, coordinador)["por_semana"]
    assert [s["inicio"] for s in semanas] == [(lunes - timedelta(weeks=11 - i)).isoformat() for i in range(12)]
    assert [s["total"] for s in semanas] == [0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 1, 1]


def test_semanas_respetan_sector_y_terminan_en_hasta(client, datos, coordinador):
    hoy = hoy_local()
    lunes = hoy - timedelta(days=hoy.weekday())
    datos("bache", creado_en=local(lunes - timedelta(weeks=20), 10))
    datos("bache", colonia=datos.lejana, creado_en=local(lunes - timedelta(weeks=20), 11))
    hasta = lunes - timedelta(weeks=20) + timedelta(days=2)

    semanas = tablero(client, coordinador, hasta=hasta.isoformat(), sector_id=datos.sur.id)["por_semana"]
    assert semanas[-1]["inicio"] == (lunes - timedelta(weeks=20)).isoformat()
    assert [s["total"] for s in semanas] == [0] * 11 + [1]


# --- 5. Baches más longevos y longevidad por colonia ----------------------------------------------
def test_mas_longevos_y_promedio_por_colonia(client, datos, coordinador):
    hoy = hoy_local()
    for dias in range(1, 13):  # 12 abiertos en la colonia de prueba, de 1 a 12 días
        datos("bache", ("recibido", "validado", "en_reparacion")[dias % 3], creado_en=local(hoy - timedelta(days=dias)))
    datos("bache", colonia=datos.lejana, creado_en=local(hoy - timedelta(days=30)))
    datos("bache", colonia=datos.lejana, creado_en=local(hoy - timedelta(days=10)))
    datos("bache", "reparado", creado_en=local(hoy - timedelta(days=99)))  # cerrado: no es longevo
    datos("encharcamiento", "historico", creado_en=local(hoy - timedelta(days=99)))

    cuerpo = tablero(client, coordinador)
    longevos = cuerpo["mas_longevos"]
    assert [b["antiguedad_dias"] for b in longevos] == [30, 12, 11, 10, 10, 9, 8, 7, 6, 5]
    assert longevos[0]["colonia"]["nombre"] == "Colonia Lejana" and longevos[0]["folio"].startswith("BCH-")
    assert set(longevos[0]) == {"id", "folio", "calle", "colonia", "estado", "antiguedad_dias"}
    assert [(c["colonia"]["nombre"], c["abiertos"], c["promedio_dias"]) for c in cuerpo["longevidad_por_colonia"]] == [
        ("Colonia Lejana", 2, 20.0), ("Partido Escobedo", 12, 6.5),
    ]
    # Con filtro de sector solo queda la colonia del sector Sur
    sur = tablero(client, coordinador, sector_id=datos.sur.id)
    assert [b["antiguedad_dias"] for b in sur["mas_longevos"]] == [30, 10]


# --- Roles, validación y privacidad -------------------------------------------------------------
def test_sin_token_401(client, catalogo):
    r = client.get("/api/tablero")
    assert r.status_code == 401 and r.json()["codigo"] == "NO_AUTENTICADO"


@pytest.mark.parametrize("rol", ["ciudadano", "moderador"])
def test_otros_roles_403(client, crear_usuario, rol):
    persona = crear_usuario(f"{rol}2@ejemplo.test", rol=rol)
    r = client.get("/api/tablero", headers=encabezado_de(persona))
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"


@pytest.mark.parametrize(
    ("params", "campo"),
    [
        ({"desde": "2026-11-10", "hasta": "2026-11-01"}, "hasta"),
        ({"sector_id": 999}, "sector_id"),
        ({"sector_id": 0}, "sector_id"),
        ({"desde": "10/11/2026"}, "desde"),
    ],
)
def test_filtro_invalido_422(client, catalogo, coordinador, params, campo):
    r = client.get("/api/tablero", params=params, headers=encabezado_de(coordinador))
    assert r.status_code == 422 and r.json()["codigo"] == "VALIDACION"
    assert campo in r.json()["campos"]


def test_la_respuesta_no_trae_datos_personales(client, datos, coordinador, ciudadano):
    datos("bache")
    datos("encharcamiento")
    cuerpo = tablero(client, coordinador)
    assert not (llaves_de(cuerpo) & LLAVES_PROHIBIDAS)
    assert ciudadano.correo not in str(cuerpo) and ciudadano.nombre not in str(cuerpo)


# --- Rendimiento (RNF-06): las consultas no crecen con el número de reportes -----------------------
def test_cientos_de_reportes_mismas_consultas_y_cifras_correctas(client, db, datos, coordinador):
    sentencias = []

    def contar(_conexion, _cursor, sql, *_args):
        sentencias.append(sql)

    hoy = hoy_local()
    datos("bache", creado_en=local(hoy - timedelta(days=3)))
    engine = db.get_bind()
    event.listen(engine, "before_cursor_execute", contar)
    try:
        tablero(client, coordinador)
        con_uno = len(sentencias)

        for i in range(400):
            colonia = datos.lejana if i % 2 else None
            if i % 5 == 4:
                datos("encharcamiento", "historico", colonia=colonia, creado_en=local(hoy - timedelta(days=i % 70)),
                      guardar=False)
            else:
                datos("bache", ("recibido", "validado", "en_reparacion", "reparado")[i % 4], colonia=colonia,
                      creado_en=local(hoy - timedelta(days=i % 70)), guardar=False)
        db.commit()
        sentencias.clear()
        cuerpo = tablero(client, coordinador)
        assert len(sentencias) == con_uno  # mismo número de consultas con 1 que con 401 reportes
    finally:
        event.remove(engine, "before_cursor_execute", contar)

    assert cuerpo["totales"]["total"] == 401
    assert cuerpo["totales"]["encharcamiento"] == 80 and cuerpo["totales"]["bache"] == 321
    assert sum(c["abiertos"] for c in cuerpo["longevidad_por_colonia"]) == 241
    # Los 70 días caben en las 12 semanas (84 días): la serie suma todos los reportes
    assert sum(s["total"] for s in cuerpo["por_semana"]) == 401
