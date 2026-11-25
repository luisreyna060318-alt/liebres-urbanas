"""Moderación: bandeja, validar y rechazar (HU-05.1)."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select, update

from app.core.tiempo import ahora_utc
from app.models import Colonia, HistorialEstado, MotivoRechazo, Reporte
from tests.conftest import LLAVES_PROHIBIDAS, encabezado_de, llaves_de

BANDEJA = "/api/moderacion/bandeja"


@pytest.fixture()
def datos(db, catalogo, ciudadano):
    """Catálogo + una segunda colonia + motivos de rechazo + una fábrica de reportes insertados directo."""
    otra = Colonia(nombre="Centro", sector_id=catalogo["sector"].id)
    duplicado = MotivoRechazo(codigo="duplicado", nombre="Duplicado")
    otro = MotivoRechazo(codigo="otro", nombre="Otro", pide_explicacion=True)
    viejo = MotivoRechazo(codigo="viejo", nombre="Motivo retirado", activo=False)
    db.add_all([otra, duplicado, otro, viejo])
    db.commit()
    contador = {"n": 0}

    def _reporte(categoria="bache", estado=None, dias=0, colonia=None, tipo="bache", **extra):
        contador["n"] += 1
        n = contador["n"]
        comunes = dict(autor_id=ciudadano.id, colonia_id=(colonia or catalogo["colonia"]).id, calle="Calle Ficticia",
                       lat=31.7, lon=-106.4, creado_en=ahora_utc() - timedelta(days=dias), **extra)
        if categoria == "bache":
            r = Reporte(folio=f"BCH-2026-{n:06d}", categoria="bache", tipo_dano_id=catalogo["tipos"][tipo].id,
                        severidad="baja", tamano="chico", carril="orilla", estado=estado or "recibido", **comunes)
        else:
            r = Reporte(folio=f"ENC-2026-{n:06d}", categoria="encharcamiento", nivel_agua="cubre_carril",
                        vigente_hasta=ahora_utc() + timedelta(hours=6), estado=estado or "activo", **comunes)
        db.add(r)
        db.commit()
        return r

    return {"otra": otra, "duplicado": duplicado, "otro": otro, "viejo": viejo, "reporte": _reporte, **catalogo}


def folios(respuesta) -> list[str]:
    return [i["folio"] for i in respuesta.json()["items"]]


# --- Bandeja ---------------------------------------------------------------------------------------
def test_bandeja_solo_baches_recibidos_del_mas_antiguo_al_mas_reciente(client, moderador, datos):
    nuevo = datos["reporte"](dias=0)
    antiguo = datos["reporte"](dias=5)
    medio = datos["reporte"](dias=2)
    datos["reporte"](estado="validado", dias=9)
    datos["reporte"](estado="rechazado", dias=9)
    datos["reporte"]("encharcamiento", dias=9)

    r = client.get(BANDEJA, headers=encabezado_de(moderador))
    assert r.status_code == 200
    assert folios(r) == [antiguo.folio, medio.folio, nuevo.folio]
    cuerpo = r.json()
    assert cuerpo["total"] == 3 and cuerpo["tam"] == 10 and cuerpo["pagina"] == 1
    assert all(i["estado"] == "recibido" and i["sin_validar"] for i in cuerpo["items"])
    assert not (llaves_de(cuerpo) & LLAVES_PROHIBIDAS)  # privacidad: sin autor


def test_bandeja_filtra_por_colonia_y_por_tipo(client, moderador, datos):
    en_centro = datos["reporte"](colonia=datos["otra"])
    grieta = datos["reporte"](tipo="grieta")
    datos["reporte"]()

    h = encabezado_de(moderador)
    assert folios(client.get(BANDEJA, params={"colonia_id": datos["otra"].id}, headers=h)) == [en_centro.folio]
    assert folios(client.get(BANDEJA, params={"tipo_dano_codigo": "grieta"}, headers=h)) == [grieta.folio]
    ambos = client.get(BANDEJA, params={"tipo_dano_codigo": "grieta", "colonia_id": datos["otra"].id}, headers=h)
    assert ambos.json()["total"] == 0


def test_bandeja_pagina_de_10_en_10(client, moderador, datos):
    creados = [datos["reporte"](dias=20 - i) for i in range(12)]
    h = encabezado_de(moderador)
    primera = client.get(BANDEJA, headers=h).json()
    segunda = client.get(BANDEJA, params={"pagina": 2}, headers=h).json()
    assert primera["total"] == 12 and len(primera["items"]) == 10
    assert [i["folio"] for i in segunda["items"]] == [c.folio for c in creados[10:]]


def test_bandeja_vence_encharcamientos_antes_de_leer(client, moderador, datos, db):
    vencido = datos["reporte"]("encharcamiento")
    vencido.vigente_hasta = ahora_utc() - timedelta(minutes=1)
    db.commit()
    assert client.get(BANDEJA, headers=encabezado_de(moderador)).status_code == 200
    db.refresh(vencido)
    assert vencido.estado == "historico"


# --- Validar ---------------------------------------------------------------------------------------
def test_validar_deja_historial_con_actor_fecha_y_comentario(client, moderador, datos, db):
    reporte = datos["reporte"]()
    r = client.post(f"/api/reportes/{reporte.id}/validar", json={"comentario": "  Visto en sitio  "},
                    headers=encabezado_de(moderador))
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "validado" and r.json()["sin_validar"] is False
    assert not (llaves_de(r.json()) & LLAVES_PROHIBIDAS)

    fila = db.scalar(select(HistorialEstado).where(HistorialEstado.reporte_id == reporte.id))
    assert (fila.estado_anterior, fila.estado_nuevo) == ("recibido", "validado")
    assert fila.actor_id == moderador.id  # el historial interno guarda quién
    assert fila.comentario == "Visto en sitio"
    assert abs(fila.creado_en - ahora_utc()) < timedelta(minutes=1)


def test_validar_sin_comentario(client, moderador, datos):
    reporte = datos["reporte"]()
    r = client.post(f"/api/reportes/{reporte.id}/validar", json={}, headers=encabezado_de(moderador))
    assert r.status_code == 200


@pytest.mark.parametrize("estado", ["validado", "en_reparacion", "rechazado"])
def test_validar_fuera_de_recibido_responde_409(client, moderador, datos, estado):
    reporte = datos["reporte"](estado=estado)
    r = client.post(f"/api/reportes/{reporte.id}/validar", json={}, headers=encabezado_de(moderador))
    assert r.status_code == 409 and r.json()["codigo"] == "TRANSICION_INVALIDA"
    assert reporte.folio in r.json()["detail"]


def test_validar_un_encharcamiento_responde_409(client, moderador, datos):
    reporte = datos["reporte"]("encharcamiento")
    r = client.post(f"/api/reportes/{reporte.id}/validar", json={}, headers=encabezado_de(moderador))
    assert r.status_code == 409


def test_validar_reporte_inexistente_responde_404(client, moderador, datos):
    r = client.post("/api/reportes/9999/validar", json={}, headers=encabezado_de(moderador))
    assert r.status_code == 404 and r.json()["codigo"] == "NO_ENCONTRADO"


def test_comentario_de_mas_de_500_caracteres_responde_422(client, moderador, datos):
    reporte = datos["reporte"]()
    r = client.post(f"/api/reportes/{reporte.id}/validar", json={"comentario": "x" * 501},
                    headers=encabezado_de(moderador))
    assert r.status_code == 422 and "comentario" in r.json()["campos"]


@pytest.mark.parametrize(
    ("ruta", "cuerpo", "estado_previo", "otro_estado"),
    [
        ("validar", {}, "recibido", "rechazado"),
        ("rechazar", {"motivo": "duplicado"}, "recibido", "validado"),
        ("estado", {"estado": "en_reparacion"}, "validado", "en_reparacion"),
    ],
)
def test_cambio_de_estado_relee_la_fila_antes_de_decidir(client, moderador, datos, db, ruta, cuerpo, estado_previo,
                                                        otro_estado):
    """Simula a otro moderador que ya cambió el reporte: la sesión conserva el objeto viejo en memoria, pero la
    ruta relee la fila (with_for_update) y responde 409 sin escribir un segundo historial. SQLite no bloquea filas:
    aquí se prueba la relectura; el bloqueo en sí lo hace PostgreSQL."""
    reporte = datos["reporte"](estado=estado_previo)
    # Cambio "por fuera" del ORM, sin commit: el objeto en memoria sigue diciendo estado_previo
    db.execute(update(Reporte.__table__).where(Reporte.__table__.c.id == reporte.id).values(estado=otro_estado))
    assert reporte.estado == estado_previo
    if "motivo" in cuerpo:
        cuerpo = {"motivo_rechazo_id": datos[cuerpo["motivo"]].id}
    r = client.post(f"/api/reportes/{reporte.id}/{ruta}", json=cuerpo, headers=encabezado_de(moderador))
    assert r.status_code == 409 and r.json()["codigo"] == "TRANSICION_INVALIDA", r.text
    assert filas_de_historial(db, reporte) == 0


# --- Rechazar --------------------------------------------------------------------------------------
def rechazar(client, usuario, reporte_id, **cuerpo):
    return client.post(f"/api/reportes/{reporte_id}/rechazar", json=cuerpo, headers=encabezado_de(usuario))


def test_rechazar_exige_motivo(client, moderador, datos):
    reporte = datos["reporte"]()
    r = rechazar(client, moderador, reporte.id)
    assert r.status_code == 422 and "motivo_rechazo_id" in r.json()["campos"]


@pytest.mark.parametrize("cual", ["inexistente", "inactivo"])
def test_rechazar_con_motivo_inexistente_o_inactivo_responde_422(client, moderador, datos, cual):
    reporte = datos["reporte"]()
    motivo_id = 9999 if cual == "inexistente" else datos["viejo"].id
    r = rechazar(client, moderador, reporte.id, motivo_rechazo_id=motivo_id)
    assert r.status_code == 422 and r.json()["campos"] == {"motivo_rechazo_id": "Elige un motivo de la lista"}


def filas_de_historial(db, reporte) -> int:
    return db.scalar(select(func.count()).select_from(HistorialEstado).where(HistorialEstado.reporte_id == reporte.id))


@pytest.mark.parametrize("texto", [None, "   "])
def test_motivo_otro_exige_explicacion(client, moderador, datos, db, texto):
    reporte = datos["reporte"]()
    r = rechazar(client, moderador, reporte.id, motivo_rechazo_id=datos["otro"].id, motivo_texto=texto)
    assert r.status_code == 422 and "motivo_texto" in r.json()["campos"]
    # Se relee de la base: el 422 no debe dejar el estado cambiado ni una fila de historial
    db.refresh(reporte)
    assert reporte.estado == "recibido"
    assert filas_de_historial(db, reporte) == 0


def test_rechazar_guarda_motivo_y_el_autor_lo_ve(client, moderador, ciudadano, datos, db):
    reporte = datos["reporte"]()
    r = rechazar(client, moderador, reporte.id, motivo_rechazo_id=datos["otro"].id,
                 motivo_texto="Está dentro de un estacionamiento privado", comentario="No es vía pública")
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "rechazado"
    assert "motivo_rechazo" not in r.json()  # el motivo solo lo ve el autor

    fila = db.scalar(select(HistorialEstado).where(HistorialEstado.reporte_id == reporte.id))
    assert fila.actor_id == moderador.id and fila.comentario == "No es vía pública"

    mio = client.get("/api/mis-reportes", headers=encabezado_de(ciudadano)).json()["items"][0]
    assert mio["motivo_rechazo"] == {"nombre": "Otro", "texto": "Está dentro de un estacionamiento privado"}


def test_motivo_sin_explicacion_obligatoria(client, moderador, datos):
    reporte = datos["reporte"]()
    r = rechazar(client, moderador, reporte.id, motivo_rechazo_id=datos["duplicado"].id)
    assert r.status_code == 200


@pytest.mark.parametrize("estado", ["activo", "historico"])
def test_rechazar_encharcamiento_activo_o_historico(client, moderador, datos, estado):
    reporte = datos["reporte"]("encharcamiento", estado=estado)
    r = rechazar(client, moderador, reporte.id, motivo_rechazo_id=datos["duplicado"].id)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "rechazado"


@pytest.mark.parametrize("categoria,estado", [("bache", "validado"), ("bache", "rechazado"),
                                              ("encharcamiento", "rechazado")])
def test_rechazar_salto_invalido_responde_409(client, moderador, datos, categoria, estado):
    reporte = datos["reporte"](categoria, estado=estado)
    r = rechazar(client, moderador, reporte.id, motivo_rechazo_id=datos["duplicado"].id)
    assert r.status_code == 409 and r.json()["codigo"] == "TRANSICION_INVALIDA"


# --- Roles -----------------------------------------------------------------------------------------
@pytest.mark.parametrize("metodo,ruta", [("get", BANDEJA), ("post", "/api/reportes/{id}/validar"),
                                         ("post", "/api/reportes/{id}/rechazar")])
def test_matriz_de_roles(client, datos, ciudadano, coordinador, moderador, metodo, ruta):
    reporte = datos["reporte"]()
    url = ruta.format(id=reporte.id)
    cuerpo = {"motivo_rechazo_id": datos["duplicado"].id} if "rechazar" in url else {}

    def llamar(headers=None):
        if metodo == "get":
            return client.get(url, headers=headers)
        return client.post(url, json=cuerpo, headers=headers)

    assert llamar().status_code == 401
    assert llamar(encabezado_de(ciudadano)).status_code == 403
    # El coordinador NO modera: la tabla de endpoints (#26 a #28) solo da permiso al moderador
    assert llamar(encabezado_de(coordinador)).json()["codigo"] == "SIN_PERMISO"
    assert llamar(encabezado_de(moderador)).status_code == 200
