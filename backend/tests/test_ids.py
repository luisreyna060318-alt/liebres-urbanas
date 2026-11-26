"""Ids enteros fuera de rango (hallazgo S4 de la auditoría de seguridad).

Un id mayor que el `integer` de PostgreSQL (2 147 483 647) llegaba a la base y respondía 500. Ahora las rutas,
los filtros ?x_id= y los campos de entrada usan IdEntero (schemas/comun.py): fuera de 1..ID_MAX responden
422 VALIDACION con `campos`, la forma de siempre. SQLite no tiene ese límite, por eso se prueba la validación.
"""

import pytest

from app.core.reglas import ID_MAX
from app.core.security import crear_token
from tests.conftest import datos_bache, encabezado_de

FUERA_DE_RANGO = [99999999999, ID_MAX + 1, 0, -1]

# (método, ruta con {id}, rol que puede usarla o None si es pública, campo que debe marcar el 422)
# Al menos una ruta de cada router que recibe ids.
CASOS = [
    ("get", "/api/reportes/{id}", None, "reporte_id"),  # consulta
    ("get", "/api/reportes?colonia_id={id}", None, "colonia_id"),  # consulta
    ("get", "/api/reportes?sector_id={id}", None, "sector_id"),  # consulta
    ("get", "/api/colonias?sector_id={id}", None, "sector_id"),  # catalogos
    ("post", "/api/reportes/{id}/confirmaciones", "ciudadano", "reporte_id"),  # reportes
    ("put", "/api/reportes/{id}", "ciudadano", "reporte_id"),  # reportes
    ("delete", "/api/reportes/{id}", "ciudadano", "reporte_id"),  # reportes
    ("get", "/api/moderacion/bandeja?colonia_id={id}", "moderador", "colonia_id"),  # moderacion
    ("get", "/api/moderacion/seguimiento?colonia_id={id}", "coordinador", "colonia_id"),  # moderacion
    ("post", "/api/reportes/{id}/validar", "moderador", "reporte_id"),  # moderacion
    ("post", "/api/reportes/{id}/rechazar", "moderador", "reporte_id"),  # moderacion
    ("post", "/api/reportes/{id}/estado", "moderador", "reporte_id"),  # moderacion
    ("put", "/api/usuarios/{id}/rol", "coordinador", "usuario_id"),  # usuarios
    ("put", "/api/usuarios/{id}/suspension", "coordinador", "usuario_id"),  # usuarios
    ("get", "/api/tablero?sector_id={id}", "coordinador", "sector_id"),  # tablero
    ("put", "/api/sectores/{id}", "coordinador", "sector_id"),  # admin_catalogos
    ("put", "/api/colonias/{id}", "coordinador", "colonia_id"),  # admin_catalogos
    ("delete", "/api/colonias/{id}", "coordinador", "colonia_id"),  # admin_catalogos
]


def _encabezados(crear_usuario, rol):
    if rol is None:
        return {}
    return encabezado_de(crear_usuario(f"{rol}-ids@ejemplo.test", rol=rol))


def _pedir(client, metodo, ruta, headers, cuerpo=None):
    if metodo in ("get", "delete"):
        return client.request(metodo.upper(), ruta, headers=headers)
    return client.request(metodo.upper(), ruta, headers=headers, json=cuerpo if cuerpo is not None else {})


def _assert_422(r, campo):
    assert r.status_code == 422, r.text
    cuerpo = r.json()
    assert cuerpo["codigo"] == "VALIDACION"
    assert campo in cuerpo["campos"], cuerpo


@pytest.mark.parametrize("valor", [99999999999, 0])
@pytest.mark.parametrize(("metodo", "ruta", "rol", "campo"), CASOS, ids=lambda c: str(c))
def test_id_de_ruta_o_filtro_fuera_de_rango_responde_422(client, crear_usuario, metodo, ruta, rol, campo, valor):
    r = _pedir(client, metodo, ruta.format(id=valor), _encabezados(crear_usuario, rol))
    _assert_422(r, campo)


@pytest.mark.parametrize("valor", FUERA_DE_RANGO)
def test_colonia_id_del_alta_fuera_de_rango_responde_422(client, ciudadano, catalogo, valor):
    r = client.post("/api/reportes/baches", json=datos_bache(valor), headers=encabezado_de(ciudadano))
    _assert_422(r, "colonia_id")


@pytest.mark.parametrize("valor", [99999999999, 0])
def test_colonia_id_del_encharcamiento_fuera_de_rango_responde_422(client, ciudadano, catalogo, valor):
    cuerpo = {"lat": 31.7, "lon": -106.43, "calle": "Av. Prueba", "colonia_id": valor, "nivel_agua": "a_un_lado"}
    r = client.post("/api/reportes/encharcamientos", json=cuerpo, headers=encabezado_de(ciudadano))
    _assert_422(r, "colonia_id")


@pytest.mark.parametrize("valor", [99999999999, 0])
def test_motivo_rechazo_id_fuera_de_rango_responde_422(client, moderador, valor):
    r = client.post("/api/reportes/1/rechazar", json={"motivo_rechazo_id": valor}, headers=encabezado_de(moderador))
    _assert_422(r, "motivo_rechazo_id")


@pytest.mark.parametrize("valor", [99999999999, 0])
def test_sector_id_de_la_colonia_fuera_de_rango_responde_422(client, coordinador, valor):
    r = client.post("/api/colonias", json={"nombre": "Colonia Ficticia", "sector_id": valor},
                    headers=encabezado_de(coordinador))
    _assert_422(r, "sector_id")


def test_token_con_id_fuera_de_rango_responde_401(client):
    """Un `sub` enorme (solo posible con la clave) ya no llega a la base: es un token inválido."""
    r = client.get("/api/mis-reportes", headers={"Authorization": f"Bearer {crear_token(99999999999)}"})
    assert r.status_code == 401 and r.json()["codigo"] == "NO_AUTENTICADO"


# --- Los ids válidos siguen funcionando ---------------------------------------------------------------
def test_ids_validos_siguen_funcionando(client, ciudadano, coordinador, catalogo):
    colonia_id, sector_id = catalogo["colonia"].id, catalogo["sector"].id
    r = client.post("/api/reportes/baches", json=datos_bache(colonia_id), headers=encabezado_de(ciudadano))
    assert r.status_code == 201, r.text
    reporte_id = r.json()["id"]

    assert client.get(f"/api/reportes/{reporte_id}").status_code == 200
    assert client.get(f"/api/reportes?colonia_id={colonia_id}").json()["total"] == 1
    assert client.get(f"/api/reportes?sector_id={sector_id}").json()["total"] == 1
    assert client.get(f"/api/colonias?sector_id={sector_id}").json()["total"] == 1
    assert client.get(f"/api/tablero?sector_id={sector_id}", headers=encabezado_de(coordinador)).status_code == 200
    # El tope mismo es válido: no existe, así que es 404 (no 422 ni 500)
    assert client.get(f"/api/reportes/{ID_MAX}").status_code == 404
