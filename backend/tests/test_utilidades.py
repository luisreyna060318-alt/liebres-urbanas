"""Folios, distancia, fechas, restricciones de la base y forma de los errores."""

import re
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.geo import caja, distancia_m
from app.core.tiempo import a_hora_local, como_utc
from app.models import Reporte, Usuario
from app.services.folios import generar_folio


# --- Folios (RN-03) -------------------------------------------------------------------------------
def test_folios_consecutivos_con_formato(db):
    folios = [generar_folio(db, "BCH", 2026) for _ in range(3)]
    assert folios == ["BCH-2026-000001", "BCH-2026-000002", "BCH-2026-000003"]
    assert all(re.fullmatch(r"BCH-\d{4}-\d{6}", f) for f in folios)


def test_folios_independientes_por_prefijo_y_anio(db):
    assert generar_folio(db, "BCH", 2026) == "BCH-2026-000001"
    assert generar_folio(db, "ENC", 2026) == "ENC-2026-000001"
    assert generar_folio(db, "BCH", 2027) == "BCH-2027-000001"
    assert generar_folio(db, "BCH", 2026) == "BCH-2026-000002"
    db.commit()
    assert generar_folio(db, "ENC", 2026) == "ENC-2026-000002"  # sigue después del commit


def test_folio_con_prefijo_desconocido(db):
    with pytest.raises(ValueError):
        generar_folio(db, "XYZ", 2026)


# --- Distancias -----------------------------------------------------------------------------------
def test_distancia_valores_conocidos():
    assert distancia_m(31.7, -106.4, 31.7, -106.4) == 0
    # Un grado de latitud mide ~111.19 km con el radio medio de la Tierra
    assert distancia_m(31.0, -106.4, 32.0, -106.4) == pytest.approx(111_195, rel=1e-3)
    # 0.00027° de latitud son ~30 m (radio de duplicado de baches)
    assert distancia_m(31.7, -106.4, 31.70027, -106.4) == pytest.approx(30.0, abs=0.1)
    # Simétrica
    assert distancia_m(31.69, -106.42, 31.74, -106.48) == pytest.approx(distancia_m(31.74, -106.48, 31.69, -106.42))


def test_caja_contiene_los_puntos_del_radio():
    lat, lon = 31.7, -106.4
    lat_min, lat_max, lon_min, lon_max = caja(lat, lon, 50)
    # Puntos a 50 m al norte y al este quedan dentro de la caja
    assert lat_min < lat + 50 / 111_195 < lat_max
    este = lon + 50 / (111_195 * 0.8508)  # cos(31.7°) ≈ 0.8508
    assert distancia_m(lat, lon, lat, este) == pytest.approx(50, abs=0.5)
    assert lon_min < este < lon_max


# --- Fechas (RN-02) -------------------------------------------------------------------------------
def test_fecha_sin_zona_se_trata_como_utc():
    assert como_utc(datetime(2026, 11, 24, 21, 5)) == datetime(2026, 11, 24, 21, 5, tzinfo=UTC)
    # 21:05 UTC son las 14:05 en Ciudad Juárez (UTC-7)
    assert a_hora_local(datetime(2026, 11, 24, 21, 5, tzinfo=UTC)).hour == 14


def test_sqlite_devuelve_fechas_con_zona_utc(db, crear_reporte):
    reporte = crear_reporte("encharcamiento")
    db.expire_all()
    leido = db.get(Reporte, reporte.id)
    assert leido.creado_en.tzinfo is not None and leido.creado_en.utcoffset() == timedelta(0)
    assert leido.vigente_hasta > leido.creado_en


# --- Restricciones de la base ---------------------------------------------------------------------
def test_correo_se_normaliza_y_es_unico(db, crear_usuario):
    usuario = crear_usuario("  Mixto@Ejemplo.TEST ")
    assert usuario.correo == "mixto@ejemplo.test"
    db.add(Usuario(nombre="Otra", correo="MIXTO@ejemplo.test", password_hash="x"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_check_rechaza_campos_de_otra_categoria(db, crear_reporte):
    reporte = crear_reporte("bache")
    reporte.nivel_agua = "intransitable"  # campo de encharcamiento en un bache
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_check_descripcion_maxima(db, crear_reporte):
    reporte = crear_reporte("bache")
    reporte.descripcion = "x" * 501
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


# --- Forma de los errores (CONTRATO_API, sección 1) -----------------------------------------------
def test_ruta_inexistente_con_formato_de_error(client):
    r = client.get("/api/no-existe")
    assert r.status_code == 404
    assert r.json() == {"detail": "El recurso no existe", "codigo": "NO_ENCONTRADO"}


def test_error_de_validacion_trae_campos_en_espanol(client):
    r = client.post("/api/auth/login", json={"correo": "ana@ejemplo.test"})
    assert r.status_code == 422
    assert r.json() == {"detail": "Revisa los datos marcados", "codigo": "VALIDACION",
                        "campos": {"password": "Este campo es obligatorio"}}


def test_cuerpo_que_no_es_json(client):
    r = client.post("/api/auth/login", content="{esto no es json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    assert r.json()["codigo"] == "VALIDACION" and "campos" in r.json()


def test_cors_solo_para_el_frontend_configurado(client):
    permitido = client.options("/api/reglas", headers={"Origin": "http://localhost:5173",
                                                       "Access-Control-Request-Method": "GET"})
    assert permitido.headers.get("access-control-allow-origin") == "http://localhost:5173"
    ajeno = client.options("/api/reglas", headers={"Origin": "https://sitio-ajeno.test",
                                                   "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in ajeno.headers
