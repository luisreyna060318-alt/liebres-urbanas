"""Mis reportes: consultar, corregir y eliminar (HU-02.5)."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select, update

from app.core.tiempo import ahora_utc
from app.models import Confirmacion, HistorialEstado, MotivoRechazo, Reporte
from app.services.estados import registrar_cambio_estado
from tests.conftest import LLAVES_PROHIBIDAS, datos_bache, encabezado_de, llaves_de


@pytest.fixture()
def alta(client, ciudadano, catalogo):
    def _alta(n: int = 0, usuario=None, **cambios):
        r = client.post(
            "/api/reportes/baches", json=datos_bache(catalogo["colonia"].id, n, **cambios),
            headers=encabezado_de(usuario or ciudadano),
        )
        assert r.status_code == 201, r.text
        return r.json()

    return _alta


@pytest.fixture()
def otra(crear_usuario):
    return crear_usuario("otra@ejemplo.test")


def mis_reportes(client, usuario, pagina=1):
    return client.get("/api/mis-reportes", params={"pagina": pagina}, headers=encabezado_de(usuario))


def editar(client, usuario, reporte_id, catalogo, **cambios):
    datos = datos_bache(catalogo["colonia"].id, 0, **cambios)
    datos.pop("forzar")
    return client.put(f"/api/reportes/{reporte_id}", json=datos, headers=encabezado_de(usuario))


# --- CA1 y CA2: consultar --------------------------------------------------------------------------
def test_ca1_lista_mis_reportes_del_mas_reciente_al_mas_antiguo(client, ciudadano, alta, db):
    primero, segundo = alta(0), alta(1)
    # Un encharcamiento propio también aparece (se inserta directo: su alta llega en otra rama)
    db.add(Reporte(folio="ENC-2026-000001", categoria="encharcamiento", autor_id=ciudadano.id,
                   colonia_id=primero["colonia"]["id"], calle="Calle", lat=31.71, lon=-106.43, nivel_agua="a_un_lado",
                   vigente_hasta=ahora_utc() + timedelta(hours=6), estado="activo",
                   creado_en=ahora_utc() + timedelta(seconds=5)))
    db.commit()
    r = mis_reportes(client, ciudadano)
    assert r.status_code == 200
    datos = r.json()
    assert datos["total"] == 3 and datos["pagina"] == 1 and datos["tam"] == 10
    assert [i["folio"] for i in datos["items"]] == ["ENC-2026-000001", segundo["folio"], primero["folio"]]
    assert datos["items"][0]["puede_editar"] is False  # encharcamiento activo
    assert datos["items"][1]["puede_editar"] is True
    assert not (llaves_de(datos) & LLAVES_PROHIBIDAS)


def test_paginacion_de_10_en_10(client, ciudadano, db, catalogo):
    # Se crean directo en la base para no chocar con el límite de 10 por hora
    for n in range(23):
        db.add(Reporte(folio=f"BCH-2026-{n + 1:06d}", categoria="bache", tipo_dano_id=catalogo["tipos"]["bache"].id,
                       autor_id=ciudadano.id, colonia_id=catalogo["colonia"].id, calle="Calle", lat=31.7, lon=-106.43,
                       severidad="baja", estado="recibido", creado_en=ahora_utc() - timedelta(days=n)))
    db.commit()
    paginas = [mis_reportes(client, ciudadano, p).json() for p in (1, 2, 3, 4)]
    assert [len(p["items"]) for p in paginas] == [10, 10, 3, 0]
    assert all(p["total"] == 23 for p in paginas)
    assert paginas[0]["items"][0]["folio"] == "BCH-2026-000001"  # el más reciente
    assert paginas[2]["items"][-1]["folio"] == "BCH-2026-000023"  # el más antiguo
    assert paginas[0]["items"][9]["antiguedad_dias"] == 9


def test_solo_veo_mis_reportes(client, ciudadano, otra, alta):
    alta(0)
    alta(1, usuario=otra)
    assert mis_reportes(client, ciudadano).json()["total"] == 1


def test_ca4_sin_reportes_lista_vacia(client, otra):
    assert mis_reportes(client, otra).json() == {"items": [], "total": 0, "pagina": 1, "tam": 10}


def test_ca2_rechazado_muestra_el_motivo(client, ciudadano, moderador, alta, db):
    motivo = MotivoRechazo(codigo="otro", nombre="Otro", pide_explicacion=True)
    db.add(motivo)
    db.commit()
    reporte = db.get(Reporte, alta()["id"])
    registrar_cambio_estado(db, reporte, "rechazado", moderador, motivo_rechazo_id=motivo.id,
                            motivo_texto="Está dentro de un estacionamiento privado")
    db.commit()
    item = mis_reportes(client, ciudadano).json()["items"][0]
    assert item["estado"] == "rechazado" and item["puede_editar"] is False
    assert item["motivo_rechazo"] == {"nombre": "Otro", "texto": "Está dentro de un estacionamiento privado"}


def test_pagina_invalida_responde_422(client, ciudadano):
    assert mis_reportes(client, ciudadano, 0).status_code == 422


@pytest.mark.parametrize("rol", ["moderador", "coordinador"])
def test_mis_reportes_solo_ciudadano(client, crear_usuario, rol):
    assert mis_reportes(client, crear_usuario(f"{rol}@ejemplo.test", rol=rol)).status_code == 403
    assert client.get("/api/mis-reportes").status_code == 401


# --- CA3: corregir ------------------------------------------------------------------------------
def test_ca3_corregir_en_recibido(client, ciudadano, alta, catalogo, db):
    original = alta()
    r = editar(client, ciudadano, original["id"], catalogo, calle="Calle Corregida", tamano="grande",
               descripcion="Ahora es más grande")
    assert r.status_code == 200
    datos = r.json()
    assert datos["calle"] == "Calle Corregida" and datos["severidad"] == "alta"
    assert datos["folio"] == original["folio"] and datos["creado_en"] == original["creado_en"]
    assert datos["estado"] == "recibido"


def test_corregir_aplica_las_validaciones_del_alta(client, ciudadano, alta, catalogo):
    reporte_id = alta()["id"]
    assert editar(client, ciudadano, reporte_id, catalogo, lat=19.43, lon=-99.13).json()["codigo"] == \
        "FUERA_DEL_MUNICIPIO"
    r = editar(client, ciudadano, reporte_id, catalogo, tipo_dano_codigo="alcantarilla_sin_tapa", senalizado=None)
    assert r.status_code == 422 and "senalizado" in r.json()["campos"]
    r = editar(client, ciudadano, reporte_id, catalogo, colonia_id=catalogo["inactiva"].id)
    assert r.status_code == 422 and "colonia_id" in r.json()["campos"]


def test_corregir_no_busca_duplicados(client, ciudadano, otra, alta, catalogo):
    alta(5, usuario=otra)
    propio = alta(0)
    lat, lon = datos_bache(catalogo["colonia"].id, 5)["lat"], datos_bache(catalogo["colonia"].id, 5)["lon"]
    assert editar(client, ciudadano, propio["id"], catalogo, lat=lat, lon=lon).status_code == 200


def test_otro_usuario_no_puede_corregir_ni_borrar(client, otra, alta, catalogo, db):
    reporte_id = alta()["id"]
    r = editar(client, otra, reporte_id, catalogo, calle="Mía")
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    r = client.delete(f"/api/reportes/{reporte_id}", headers=encabezado_de(otra))
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    assert db.get(Reporte, reporte_id).calle == "Av. Tecnológico"


@pytest.mark.parametrize("estado", ["validado", "rechazado"])
def test_estado_cambiado_responde_409(client, ciudadano, moderador, alta, catalogo, db, estado):
    reporte_id = alta()["id"]
    registrar_cambio_estado(db, db.get(Reporte, reporte_id), estado, moderador)
    db.commit()
    r = editar(client, ciudadano, reporte_id, catalogo, calle="Tarde")
    assert r.status_code == 409 and r.json()["codigo"] == "REPORTE_NO_EDITABLE"
    r = client.delete(f"/api/reportes/{reporte_id}", headers=encabezado_de(ciudadano))
    assert r.status_code == 409 and r.json()["codigo"] == "REPORTE_NO_EDITABLE"
    assert db.get(Reporte, reporte_id) is not None  # RN-07: no se borra


def test_editar_o_borrar_relee_la_fila_antes_de_decidir(client, ciudadano, alta, catalogo, db):
    """S3: simula a un moderador que validó el reporte en ese instante. La sesión conserva el objeto viejo
    («recibido») en memoria, pero la ruta relee la fila (with_for_update) y responde 409 sin borrar ni editar.
    SQLite no bloquea filas: aquí se prueba la relectura; el bloqueo en sí lo hace PostgreSQL."""
    reporte_id = alta()["id"]
    reporte = db.get(Reporte, reporte_id)
    assert reporte.estado == "recibido"  # cargado en memoria
    historial_antes = db.scalar(select(func.count()).select_from(HistorialEstado))
    # Cambio "por fuera" del ORM, sin commit: el objeto en memoria sigue diciendo «recibido»
    db.execute(update(Reporte.__table__).where(Reporte.__table__.c.id == reporte_id).values(estado="validado"))
    assert reporte.estado == "recibido"

    r = client.delete(f"/api/reportes/{reporte_id}", headers=encabezado_de(ciudadano))
    assert r.status_code == 409 and r.json()["codigo"] == "REPORTE_NO_EDITABLE", r.text
    r = editar(client, ciudadano, reporte_id, catalogo, calle="Calle cambiada a destiempo")
    assert r.status_code == 409 and r.json()["codigo"] == "REPORTE_NO_EDITABLE", r.text

    db.expire_all()
    reporte = db.get(Reporte, reporte_id)
    assert reporte is not None and reporte.estado == "validado"  # RN-07: sigue ahí
    assert reporte.calle != "Calle cambiada a destiempo"
    assert db.scalar(select(func.count()).select_from(HistorialEstado)) == historial_antes


def test_reporte_inexistente_responde_404(client, ciudadano, catalogo):
    assert editar(client, ciudadano, 9999, catalogo).status_code == 404
    assert client.delete("/api/reportes/9999", headers=encabezado_de(ciudadano)).status_code == 404


def test_moderador_no_edita_ni_borra(client, moderador, alta, catalogo):
    reporte_id = alta()["id"]
    assert editar(client, moderador, reporte_id, catalogo).json()["codigo"] == "SIN_PERMISO"
    assert client.delete(f"/api/reportes/{reporte_id}", headers=encabezado_de(moderador)).status_code == 403


# --- CA3: eliminar ------------------------------------------------------------------------------
def test_eliminar_en_recibido_borra_tambien_historial_y_confirmaciones(client, ciudadano, otra, alta, db):
    reporte_id = alta()["id"]
    client.post(f"/api/reportes/{reporte_id}/confirmaciones", json={"tipo": "confirma"}, headers=encabezado_de(otra))
    r = client.delete(f"/api/reportes/{reporte_id}", headers=encabezado_de(ciudadano))
    assert r.status_code == 204 and r.content == b""
    db.expire_all()
    assert db.get(Reporte, reporte_id) is None
    assert db.scalar(select(func.count()).select_from(HistorialEstado)) == 0
    assert db.scalar(select(func.count()).select_from(Confirmacion)) == 0
    assert mis_reportes(client, ciudadano).json()["total"] == 0


def test_eliminar_sin_token_responde_401(client, alta):
    assert client.delete(f"/api/reportes/{alta()['id']}").status_code == 401
