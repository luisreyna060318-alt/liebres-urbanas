"""Semilla de demostración (RNF-09): colonias desde CSV y 500 reportes ficticios con historial coherente.

Las pruebas usan un CSV de prueba con colonias inventadas (tests/datos), no el catálogo real de db/datos.
La base de los reportes se arma UNA vez por archivo (fixture `demo`) y las pruebas solo la leen.
"""

import re
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import seed
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, crear_engine
from app.core.geo import distancia_m
from app.core.reglas import PUNTO_RECURRENTE_DIAS, PUNTO_RECURRENTE_RADIO_M
from app.core.security import verify_password
from app.core.tiempo import a_hora_local
from app.models import Colonia, Confirmacion, HistorialEstado, MotivoRechazo, Reporte, Sector, TipoDano, Usuario
from app.services.estados import puede_pasar

CSV_PRUEBA = Path(__file__).parent / "datos" / "colonias_prueba.csv"
HOY = datetime(2026, 11, 25, 18, 0, tzinfo=UTC)  # fija, para que las pruebas no dependan del reloj
FOLIO = re.compile(r"^(BCH|ENC)-(\d{4})-(\d{6})$")


def base_sembrada(hoy: datetime = HOY):
    """Una base SQLite nueva con catálogos, cuentas demo, colonias de prueba y los 500 reportes. -> (engine, sesión)"""
    engine = crear_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False)()
    seed.sembrar(db)
    seed.cargar_colonias(db, CSV_PRUEBA)
    seed.cargar_reportes_demo(db, hoy=hoy)
    db.commit()
    return engine, db


@pytest.fixture(scope="module")
def demo():
    engine, db = base_sembrada()
    yield db
    db.close()
    engine.dispose()


def todos(db, modelo):
    return list(db.scalars(select(modelo)))


def historial_por_reporte(db) -> dict[int, list[HistorialEstado]]:
    filas = defaultdict(list)
    for fila in db.scalars(select(HistorialEstado).order_by(HistorialEstado.id)):
        filas[fila.reporte_id].append(fila)
    return filas


# --- Cantidades y reparto -------------------------------------------------------------------------
def test_son_exactamente_500_reportes_y_la_mezcla_es_razonable(demo):
    reportes = todos(demo, Reporte)
    assert len(reportes) == 500
    baches = [r for r in reportes if r.categoria == "bache"]
    assert 360 <= len(baches) <= 390  # ~75 %
    assert len(reportes) - len(baches) == 125  # ~25 % encharcamientos


def test_estan_repartidos_en_12_semanas_con_mas_volumen_reciente(demo):
    reportes = todos(demo, Reporte)
    edades = [(HOY - r.creado_en).total_seconds() / 86400 for r in reportes]
    assert min(edades) >= 0 and max(edades) <= 84  # nada futuro y nada de hace más de 12 semanas
    assert min(edades) < 1  # el más reciente es de hoy (el último día)
    por_semana = [sum(1 for e in edades if semana * 7 <= e < (semana + 1) * 7) for semana in range(12)]
    assert all(cuantos >= 10 for cuantos in por_semana)  # ninguna semana vacía
    assert sum(por_semana[:4]) > sum(por_semana[8:])  # las 4 más recientes pesan más que las 4 más antiguas
    assert len(set(por_semana)) > 6  # y hay variación semanal, no una rampa perfecta


def test_los_estados_de_los_baches_siguen_las_proporciones(demo):
    cuenta = defaultdict(int)
    for r in todos(demo, Reporte):
        if r.categoria == "bache":
            cuenta[r.estado] += 1
    total = sum(cuenta.values())
    esperado = {"recibido": 20, "validado": 25, "en_reparacion": 15, "reparado": 30, "rechazado": 10}
    for estado, porcentaje in esperado.items():
        assert abs(100 * cuenta[estado] / total - porcentaje) <= 1.5, (estado, cuenta)


def test_encharcamientos_la_mayoria_historicos_y_unos_pocos_activos(demo):
    cuenta = defaultdict(int)
    for r in todos(demo, Reporte):
        if r.categoria == "encharcamiento":
            cuenta[r.estado] += 1
    assert cuenta["historico"] > 100
    assert 3 <= cuenta["activo"] <= 4
    assert 1 <= cuenta["rechazado"] <= 10
    assert set(cuenta) == {"historico", "activo", "rechazado"}


def test_hay_baches_abiertos_muy_antiguos_para_el_tablero_de_longevidad(demo):
    abiertos = [
        (HOY - r.creado_en).days
        for r in todos(demo, Reporte)
        if r.categoria == "bache" and r.estado in ("recibido", "validado", "en_reparacion")
    ]
    assert sum(1 for dias in abiertos if dias >= 55) >= 10
    assert max(abiertos) <= 84


# --- Folios ---------------------------------------------------------------------------------------
def test_folios_unicos_con_formato_y_consecutivos_por_categoria_y_anio(demo):
    reportes = sorted(todos(demo, Reporte), key=lambda r: r.creado_en)
    assert len({r.folio for r in reportes}) == 500
    grupos = defaultdict(list)
    for r in reportes:
        prefijo, anio, numero = FOLIO.match(r.folio).groups()
        assert prefijo == ("BCH" if r.categoria == "bache" else "ENC")
        assert int(anio) == a_hora_local(r.creado_en).year  # el año sale de su fecha de creación
        grupos[(prefijo, anio)].append(int(numero))
    for numeros in grupos.values():
        assert numeros == list(range(1, len(numeros) + 1))  # 1, 2, 3... en orden de fecha, sin huecos


# --- Historial y estados --------------------------------------------------------------------------
def test_cada_historial_es_una_cadena_valida_con_fechas_crecientes(demo):
    historial = historial_por_reporte(demo)
    for r in todos(demo, Reporte):
        filas = historial[r.id]
        assert filas[0].estado_anterior is None  # el alta
        assert filas[0].estado_nuevo == ("recibido" if r.categoria == "bache" else "activo")
        assert filas[0].actor_id == r.autor_id
        assert filas[0].creado_en == r.creado_en
        for anterior, siguiente in zip(filas, filas[1:], strict=False):
            assert siguiente.estado_anterior == anterior.estado_nuevo
            assert puede_pasar(r.categoria, siguiente.estado_anterior, siguiente.estado_nuevo)
            assert siguiente.creado_en >= anterior.creado_en
        assert filas[-1].estado_nuevo == r.estado  # el último paso coincide con el estado del reporte
        assert filas[-1].creado_en <= HOY


def test_actores_del_historial_son_moderacion_o_sistema(demo):
    roles = {u.id: u.rol for u in todos(demo, Usuario)}
    for fila in todos(demo, HistorialEstado):
        if fila.estado_anterior is None:
            assert roles[fila.actor_id] == "ciudadano"
        elif fila.actor_id is None:  # sistema: solo el cierre de un encharcamiento activo
            assert (fila.estado_anterior, fila.estado_nuevo) == ("activo", "historico")
            assert fila.comentario in ("Venció la vigencia", "Tres personas indicaron que ya no hay agua")
        else:
            assert roles[fila.actor_id] in ("moderador", "coordinador")


def test_fecha_de_reparacion_solo_en_reparados_y_siempre_coherente(demo):
    historial = historial_por_reporte(demo)
    hoy_local = a_hora_local(HOY).date()
    reparados = 0
    for r in todos(demo, Reporte):
        if r.estado != "reparado":
            assert r.fecha_reparacion is None
            continue
        reparados += 1
        validado = next(f for f in historial[r.id] if f.estado_nuevo == "validado")
        assert a_hora_local(validado.creado_en).date() <= r.fecha_reparacion <= hoy_local
        assert r.fecha_reparacion >= a_hora_local(r.creado_en).date()
    assert reparados > 100


def test_los_encharcamientos_activos_tienen_vigencia_futura(demo):
    activos = [r for r in todos(demo, Reporte) if r.estado == "activo"]
    assert activos
    for r in activos:
        assert r.vigente_hasta > HOY
        assert r.creado_en > HOY - timedelta(hours=4)  # son de hace pocas horas
    # Los cerrados por vigencia ya vencieron
    for r in todos(demo, Reporte):
        if r.categoria == "encharcamiento" and r.estado != "activo":
            assert r.vigente_hasta <= HOY


def test_rechazados_traen_motivo_del_catalogo_y_texto_cuando_lo_pide(demo):
    motivos = {m.id: m for m in todos(demo, MotivoRechazo)}
    rechazados = [r for r in todos(demo, Reporte) if r.estado == "rechazado"]
    assert len(rechazados) > 30
    for r in rechazados:
        motivo = motivos[r.motivo_rechazo_id]
        assert bool(r.motivo_texto) == motivo.pide_explicacion
    for r in todos(demo, Reporte):
        if r.estado != "rechazado":
            assert r.motivo_rechazo_id is None and r.motivo_texto is None


def test_severidad_y_campos_por_tipo_de_dano_siguen_el_contrato(demo):
    por_codigo = {t.id: t.codigo for t in todos(demo, TipoDano)}
    vistos = set()
    for r in todos(demo, Reporte):
        if r.categoria != "bache":
            assert r.severidad is None and r.tipo_dano_id is None
            continue
        tipo = por_codigo[r.tipo_dano_id]
        vistos.add(tipo)
        assert r.severidad == seed.calcular_severidad(tipo, r.tamano, r.profundidad)
        if tipo == "alcantarilla_sin_tapa":
            assert r.severidad == "alta" and r.senalizado is not None and r.tamano is None
        else:
            assert r.tamano and r.carril and r.senalizado is None
    assert vistos == {"bache", "hundimiento", "grieta", "alcantarilla_sin_tapa"}


def test_regla_de_severidad():
    assert seed.calcular_severidad("alcantarilla_sin_tapa", None, None) == "alta"
    assert seed.calcular_severidad("bache", "grande", "baja") == "alta"
    assert seed.calcular_severidad("bache", "chico", "alta") == "alta"
    assert seed.calcular_severidad("bache", "mediano", "media") == "media"
    assert seed.calcular_severidad("grieta", "chico", None) == "baja"


# --- Confirmaciones -------------------------------------------------------------------------------
def test_contadores_iguales_a_las_filas_de_confirmaciones(demo):
    filas = todos(demo, Confirmacion)
    assert len(filas) > 200
    cuenta = defaultdict(int)
    por_reporte = {r.id: r for r in todos(demo, Reporte)}
    for c in filas:
        r = por_reporte[c.reporte_id]
        assert c.usuario_id != r.autor_id  # nadie confirma su propio reporte
        assert r.creado_en <= c.creado_en <= HOY
        assert c.tipo in (("confirma",) if r.categoria == "bache" else ("sigue", "ya_no_hay"))
        if c.tipo in ("confirma", "sigue"):
            cuenta[r.id] += 1
    for r in por_reporte.values():
        assert r.confirmaciones == cuenta[r.id]
    assert sum(1 for r in por_reporte.values() if r.confirmaciones) > 100  # "a una parte" de los reportes


def test_los_desmentidos_son_tres_y_solo_en_historicos(demo):
    por_reporte = {r.id: r for r in todos(demo, Reporte)}
    desmentidos = defaultdict(int)
    for c in todos(demo, Confirmacion):
        if c.tipo == "ya_no_hay":
            desmentidos[c.reporte_id] += 1
    assert desmentidos
    for reporte_id, cuantos in desmentidos.items():
        assert cuantos == 3
        assert por_reporte[reporte_id].estado == "historico"


# --- Ubicación ------------------------------------------------------------------------------------
def test_las_coordenadas_quedan_dentro_de_su_colonia(demo):
    colonias = {c.id: c for c in todos(demo, Colonia)}
    for r in todos(demo, Reporte):
        c = colonias[r.colonia_id]
        assert distancia_m(r.lat, r.lon, c.lat, c.lon) <= 700  # dispersión de 100 a 600 m (+ margen)
        assert r.calle and len(r.calle) <= 150


def test_hay_puntos_de_encharcamiento_recurrentes(demo):
    enc = [r for r in todos(demo, Reporte) if r.categoria == "encharcamiento"]
    candidatos = []
    for centro in enc:
        dias = {
            a_hora_local(r.creado_en).date()
            for r in enc
            if distancia_m(centro.lat, centro.lon, r.lat, r.lon) <= PUNTO_RECURRENTE_RADIO_M
        }
        if len(dias) >= PUNTO_RECURRENTE_DIAS:
            candidatos.append(centro)
    puntos = []  # se juntan los candidatos que son el mismo lugar
    for r in candidatos:
        if all(distancia_m(r.lat, r.lon, p.lat, p.lon) > 150 for p in puntos):
            puntos.append(r)
    assert len(puntos) >= 5


def test_hay_grupos_de_baches_cercanos_entre_si(demo):
    baches = [r for r in todos(demo, Reporte) if r.categoria == "bache"]
    con_vecinos = sum(
        1 for b in baches if sum(1 for o in baches if o is not b and distancia_m(b.lat, b.lon, o.lat, o.lon) <= 80) >= 2
    )
    assert con_vecinos >= 20


# --- Cuentas y privacidad -------------------------------------------------------------------------
def test_todos_los_reportes_tienen_autor_ciudadano(demo):
    roles = {u.id: u.rol for u in todos(demo, Usuario)}
    for r in todos(demo, Reporte):
        assert r.autor_id is not None and roles[r.autor_id] == "ciudadano"


def test_solo_correos_ficticios_y_las_cuentas_ficticias_no_permiten_entrar(demo):
    usuarios = todos(demo, Usuario)
    assert len(usuarios) == 33  # 3 cuentas demo (una por rol) + 30 ciudadanos ficticios
    assert all(u.correo.endswith("@liebreurbana.test") for u in usuarios)
    assert {u.rol for u in usuarios} == {"ciudadano", "moderador", "coordinador"}
    ficticios = [u for u in usuarios if re.fullmatch(r"ciudadano\d\d@liebreurbana\.test", u.correo)]
    assert len(ficticios) == 30
    for u in ficticios:
        assert not verify_password(seed.CONTRASENA_DEMO, u.password_hash)
        assert u.password_hash.startswith("$2")  # es un hash bcrypt, no una contraseña en claro


def test_la_cuenta_demo_de_ciudadano_tambien_tiene_reportes(demo):
    # La cuenta demo de ciudadano también escribe reportes: al entrar con ella "Mis reportes" no sale vacío
    demo_id = demo.scalar(select(Usuario.id).where(Usuario.correo == "ciudadano@liebreurbana.test"))
    suyos = demo.scalar(select(func.count()).select_from(Reporte).where(Reporte.autor_id == demo_id))
    assert suyos >= 3


# --- Colonias -------------------------------------------------------------------------------------
def test_colonias_suficientes_con_sector_coordenadas_y_fuente(demo):
    colonias = todos(demo, Colonia)
    assert len(colonias) >= 20
    sectores = {s.id for s in todos(demo, Sector)}
    for c in colonias:
        assert c.sector_id in sectores
        assert c.lat is not None and c.lon is not None
        assert "SEPOMEX" in c.fuente and "OpenStreetMap" in c.fuente


def test_colonias_idempotente_y_errores_claros(db, tmp_path):
    seed.sembrar(db)
    assert seed.cargar_colonias(db, CSV_PRUEBA) == 24
    db.flush()
    assert seed.cargar_colonias(db, CSV_PRUEBA) == 0
    assert db.scalar(select(func.count()).select_from(Colonia)) == 24

    with pytest.raises(seed.ErrorSemilla, match="colonias_nueva.csv"):
        seed.cargar_colonias(db, tmp_path / "colonias_nueva.csv")  # el archivo no existe

    mal_encabezado = tmp_path / "a.csv"
    mal_encabezado.write_text("nombre,sector,lat,lon\nX,Centro,31.7,-106.4\n", encoding="utf-8")
    with pytest.raises(seed.ErrorSemilla, match="encabezado"):
        seed.cargar_colonias(db, mal_encabezado)

    encabezado = ",".join(seed.ENCABEZADO_COLONIAS)
    sector_malo = tmp_path / "b.csv"
    sector_malo.write_text(f"{encabezado}\n00000,X,Colonia,Sector Inventado,31.7,-106.4\n", encoding="utf-8")
    with pytest.raises(seed.ErrorSemilla, match="sector desconocido"):
        seed.cargar_colonias(db, sector_malo)

    coordenadas_al_reves = tmp_path / "c.csv"
    coordenadas_al_reves.write_text(f"{encabezado}\n00000,X,Colonia,Centro,-106.4,31.7\n", encoding="utf-8")
    with pytest.raises(seed.ErrorSemilla, match="lat"):
        seed.cargar_colonias(db, coordenadas_al_reves)


def test_colonias_acepta_utf8_con_bom_y_no_duplica_filas_repetidas(db, tmp_path):
    seed.sembrar(db)
    encabezado = ",".join(seed.ENCABEZADO_COLONIAS)
    fila = "00000,Ñandú de Prueba,Colonia,Centro,31.7,-106.4"
    archivo = tmp_path / "bom.csv"
    archivo.write_text(f"{encabezado}\n{fila}\n{fila}\n", encoding="utf-8-sig")
    assert seed.cargar_colonias(db, archivo) == 1
    db.flush()
    assert db.scalar(select(Colonia.nombre)) == "Ñandú de Prueba"


# --- Idempotencia, determinismo y flujo completo --------------------------------------------------
def test_segunda_corrida_no_agrega_nada(demo):
    modelos = (Reporte, HistorialEstado, Confirmacion, Usuario, Colonia)

    def conteos():
        return [demo.scalar(select(func.count()).select_from(m)) for m in modelos]

    antes = conteos()
    assert antes[0] == 500 and antes[3] == 33 and antes[4] == 24
    assert seed.cargar_reportes_demo(demo, hoy=HOY) == 0
    assert seed.cargar_colonias(demo, CSV_PRUEBA) == 0
    demo.flush()
    assert conteos() == antes


def resumen(db):
    reportes = db.scalars(select(Reporte).order_by(Reporte.folio))
    colonias = {c.id: c.nombre for c in db.scalars(select(Colonia))}
    historial = historial_por_reporte(db)
    return [
        (r.folio, r.estado, r.creado_en, r.lat, r.lon, r.calle, colonias[r.colonia_id], r.severidad, r.confirmaciones,
         r.fecha_reparacion, r.vigente_hasta, [(h.estado_nuevo, h.creado_en, h.comentario) for h in historial[r.id]])
        for r in reportes
    ]  # fmt: skip


def test_misma_semilla_mismo_resultado(demo):
    engine, otra = base_sembrada()
    try:
        assert resumen(otra) == resumen(demo)
    finally:
        otra.close()
        engine.dispose()


def test_otra_semilla_cambia_los_datos(db, demo):
    seed.sembrar(db)
    seed.cargar_colonias(db, CSV_PRUEBA)
    assert seed.cargar_reportes_demo(db, hoy=HOY, semilla=7) == 500
    db.flush()
    assert resumen(db) != resumen(demo)


def test_sembrar_todo_corre_los_cuatro_pasos_y_falla_claro_sin_csv(db, tmp_path, capsys):
    with pytest.raises(seed.ErrorSemilla, match="Falta el catálogo de colonias"):
        seed.sembrar_todo(db, ruta_csv=tmp_path / "no_existe.csv", hoy=HOY)
    # Lo anterior (catálogos y cuentas) sí quedó guardado
    assert db.scalar(select(func.count()).select_from(Sector)) == 5
    assert db.scalar(select(func.count()).select_from(Usuario)) == 3
    assert db.scalar(select(func.count()).select_from(Reporte)) == 0

    seed.sembrar_todo(db, ruta_csv=CSV_PRUEBA, hoy=HOY)
    assert db.scalar(select(func.count()).select_from(Reporte)) == 500
    capsys.readouterr()
    seed.sembrar_todo(db, ruta_csv=CSV_PRUEBA, hoy=HOY)  # segunda vez: no cambia nada y lo dice
    assert "no se cargó nada" in capsys.readouterr().out
    assert db.scalar(select(func.count()).select_from(Reporte)) == 500


def test_reportes_sin_colonias_da_un_error_claro(db):
    seed.sembrar(db)
    with pytest.raises(seed.ErrorSemilla, match="cargar_colonias"):
        seed.cargar_reportes_demo(db, hoy=HOY)


# --- Rendimiento (RNF-06) -------------------------------------------------------------------------
def test_consulta_de_lista_con_500_reportes_responde_en_menos_de_un_segundo(demo):
    # Colonia con más reportes, y un estado frecuente: es la consulta típica de la lista pública
    colonia_id, _ = demo.execute(
        select(Reporte.colonia_id, func.count().label("n")).group_by(Reporte.colonia_id).order_by(func.count().desc())
    ).first()
    consulta = (
        select(Reporte)
        .where(Reporte.categoria == "bache", Reporte.estado == "validado", Reporte.colonia_id == colonia_id)
        .order_by(Reporte.creado_en.desc())
        .limit(20)
        .offset(0)
    )
    total = select(func.count()).select_from(Reporte).where(
        Reporte.categoria == "bache", Reporte.estado == "validado", Reporte.colonia_id == colonia_id
    )  # fmt: skip
    demo.expunge_all()  # sin caché de la sesión: se mide la consulta de verdad
    inicio = time.perf_counter()
    pagina = list(demo.scalars(consulta))
    cuantos = demo.scalar(total)
    segundos = time.perf_counter() - inicio
    assert pagina and cuantos >= len(pagina)
    assert segundos < 1, f"La consulta tardó {segundos:.3f} s"
