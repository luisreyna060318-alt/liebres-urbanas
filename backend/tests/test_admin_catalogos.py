"""Administración de colonias y sectores (HU-06.1): solo coordinador."""

import pytest
from sqlalchemy import func, select

from app.models import Colonia, Sector, Usuario, UsuarioColonia
from tests.conftest import encabezado_de

NUEVA = {"nombre": "Colonia Nueva Ficticia", "sector_id": None, "lat": 31.7, "lon": -106.4}


@pytest.fixture()
def admin(coordinador):
    return encabezado_de(coordinador)


@pytest.fixture()
def datos_nueva(catalogo):
    return {**NUEVA, "sector_id": catalogo["sector"].id}


def edicion(colonia: Colonia, **cambios) -> dict:
    cuerpo = {"nombre": colonia.nombre, "sector_id": colonia.sector_id, "lat": colonia.lat, "lon": colonia.lon,
              "activa": colonia.activa}
    return {**cuerpo, **cambios}


# --- Alta ------------------------------------------------------------------------------------------
def test_alta_de_colonia(client, db, admin, datos_nueva, catalogo):
    r = client.post("/api/colonias", json=datos_nueva, headers=admin)
    assert r.status_code == 201
    cuerpo = r.json()
    assert set(cuerpo) == {"id", "nombre", "sector", "activa", "lat", "lon"}
    assert cuerpo["nombre"] == "Colonia Nueva Ficticia" and cuerpo["activa"] is True
    assert cuerpo["sector"] == {"id": catalogo["sector"].id, "nombre": "Centro"}
    guardada = db.get(Colonia, cuerpo["id"])
    assert guardada.fuente  # la fuente tiene un valor por omisión (RNF-09)


def test_alta_sin_coordenadas_y_nombre_con_espacios(client, admin, datos_nueva):
    cuerpo = {"nombre": "  Colonia   Sin   Punto ", "sector_id": datos_nueva["sector_id"]}
    r = client.post("/api/colonias", json=cuerpo, headers=admin)
    assert r.status_code == 201
    assert r.json()["nombre"] == "Colonia Sin Punto" and r.json()["lat"] is None


def test_alta_con_nombre_duplicado_en_el_mismo_sector(client, admin, datos_nueva, catalogo):
    r = client.post("/api/colonias", json={**datos_nueva, "nombre": "partido escobedo"}, headers=admin)
    assert r.status_code == 409
    assert r.json()["codigo"] == "COLONIA_DUPLICADA"
    assert "nombre" in r.json()["detail"]


def test_mismo_nombre_en_otro_sector_si_se_permite(client, db, admin, datos_nueva):
    otro = Sector(nombre="Surponiente")
    db.add(otro)
    db.commit()
    r = client.post("/api/colonias", json={**datos_nueva, "nombre": "Partido Escobedo", "sector_id": otro.id},
                    headers=admin)
    assert r.status_code == 201


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"lat": 19.4, "lon": -99.1}, "lat"),  # Ciudad de México: fuera del municipio
        ({"lat": 31.7, "lon": None}, "lon"),  # falta una de las dos
        ({"lat": 95, "lon": -106.4}, "lat"),  # latitud imposible
        ({"nombre": "A"}, "nombre"),
        ({"nombre": "   "}, "nombre"),
        ({"nombre": "N" * 121}, "nombre"),
        ({"sector_id": 9999}, "sector_id"),
        ({"lat": "abc"}, "lat"),
    ],
)
def test_alta_con_datos_invalidos_da_422_con_campos(client, admin, datos_nueva, cambios, campo):
    r = client.post("/api/colonias", json={**datos_nueva, **cambios}, headers=admin)
    assert r.status_code == 422
    assert r.json()["codigo"] == "VALIDACION"
    assert campo in r.json()["campos"]


def test_alta_sin_sector_o_sin_nombre_da_422(client, admin):
    r = client.post("/api/colonias", json={}, headers=admin)
    assert r.status_code == 422
    assert {"nombre", "sector_id"} <= set(r.json()["campos"])


# --- Edición y desactivación ------------------------------------------------------------------------
def test_editar_colonia(client, db, admin, catalogo):
    colonia = catalogo["colonia"]
    r = client.put(f"/api/colonias/{colonia.id}", headers=admin,
                   json=edicion(colonia, nombre="Partido Escobedo Norte", lat=31.72, lon=-106.45))
    assert r.status_code == 200
    assert r.json()["nombre"] == "Partido Escobedo Norte" and r.json()["lat"] == 31.72
    db.refresh(colonia)
    assert colonia.nombre == "Partido Escobedo Norte"


def test_desactivar_y_reactivar_colonia(client, admin, catalogo):
    colonia = catalogo["colonia"]
    r = client.put(f"/api/colonias/{colonia.id}", json=edicion(colonia, activa=False), headers=admin)
    assert r.status_code == 200 and r.json()["activa"] is False
    # El selector de los formularios (solo activas) ya no la ofrece; la administración sí (solo_activas=false)
    publicas = [c["id"] for c in client.get("/api/colonias?tam=500").json()["items"]]
    todas = [c["id"] for c in client.get("/api/colonias?solo_activas=false&tam=500").json()["items"]]
    assert colonia.id not in publicas and colonia.id in todas
    r = client.put(f"/api/colonias/{colonia.id}", json=edicion(colonia, activa=True), headers=admin)
    assert r.json()["activa"] is True
    assert colonia.id in [c["id"] for c in client.get("/api/colonias?tam=500").json()["items"]]


def test_editar_conservando_su_propio_nombre_no_es_duplicado(client, admin, catalogo):
    colonia = catalogo["colonia"]
    assert client.put(f"/api/colonias/{colonia.id}", json=edicion(colonia), headers=admin).status_code == 200


def test_editar_a_un_nombre_ya_usado_en_el_sector_da_409(client, admin, catalogo):
    r = client.put(f"/api/colonias/{catalogo['colonia'].id}", headers=admin,
                   json=edicion(catalogo["colonia"], nombre="Colonia Cerrada"))
    assert r.status_code == 409 and r.json()["codigo"] == "COLONIA_DUPLICADA"


def test_mover_a_otro_sector_con_el_mismo_nombre_ocupado_da_409(client, db, admin, catalogo):
    otro = Sector(nombre="Nororiente")
    db.add(otro)
    db.flush()
    db.add(Colonia(nombre="Partido Escobedo", sector_id=otro.id))
    db.commit()
    r = client.put(f"/api/colonias/{catalogo['colonia'].id}", json=edicion(catalogo["colonia"], sector_id=otro.id),
                   headers=admin)
    assert r.status_code == 409


def test_editar_con_coordenadas_fuera_del_municipio_da_422(client, admin, catalogo):
    r = client.put(f"/api/colonias/{catalogo['colonia'].id}", headers=admin,
                   json=edicion(catalogo["colonia"], lat=40.7, lon=-74.0))
    assert r.status_code == 422 and "lat" in r.json()["campos"]


def test_editar_sin_activa_da_422_y_colonia_inexistente_404(client, admin, catalogo):
    colonia = catalogo["colonia"]
    sin_activa = {k: v for k, v in edicion(colonia).items() if k != "activa"}
    assert client.put(f"/api/colonias/{colonia.id}", json=sin_activa, headers=admin).status_code == 422
    r = client.put("/api/colonias/9999", json=edicion(colonia), headers=admin)
    assert r.status_code == 404 and r.json()["codigo"] == "NO_ENCONTRADO"


# --- Borrado ---------------------------------------------------------------------------------------
def test_borrar_colonia_sin_reportes(client, db, admin, catalogo):
    inactiva_id = catalogo["inactiva"].id
    r = client.delete(f"/api/colonias/{inactiva_id}", headers=admin)
    assert r.status_code == 204 and r.content == b""
    assert db.get(Colonia, inactiva_id) is None
    assert client.delete(f"/api/colonias/{inactiva_id}", headers=admin).status_code == 404


def test_borrar_colonia_quita_su_interes_de_las_personas(client, db, admin, catalogo, ciudadano):
    colonia = catalogo["colonia"]
    db.add(UsuarioColonia(usuario_id=ciudadano.id, colonia_id=colonia.id))
    db.commit()
    assert client.delete(f"/api/colonias/{colonia.id}", headers=admin).status_code == 204
    assert db.scalar(select(func.count()).select_from(UsuarioColonia)) == 0


def test_borrar_colonia_con_reportes_da_409_y_solo_se_puede_desactivar(client, db, admin, crear_reporte):
    reporte = crear_reporte("bache")
    colonia = db.get(Colonia, reporte.colonia_id)
    r = client.delete(f"/api/colonias/{colonia.id}", headers=admin)
    assert r.status_code == 409 and r.json()["codigo"] == "COLONIA_CON_REPORTES"
    assert "Desactívala" in r.json()["detail"]
    assert db.get(Colonia, colonia.id) is not None
    # Lo que sí se puede: desactivarla, y el reporte conserva su colonia
    r = client.put(f"/api/colonias/{colonia.id}", json=edicion(colonia, activa=False), headers=admin)
    assert r.status_code == 200 and r.json()["activa"] is False
    assert db.get(Colonia, colonia.id).activa is False


def test_borrar_colonia_en_carrera_con_un_reporte_nuevo_da_409(db, crear_reporte):
    """Si el reporte llega entre el conteo y el borrado, la llave foránea falla al confirmar: 409, no 500."""
    from unittest.mock import patch

    from app.core.errores import ErrorApi
    from app.services import catalogos

    reporte = crear_reporte("bache")
    colonia_id = reporte.colonia_id
    # El conteo "no ve" el reporte (como si se hubiera creado justo después de contar)
    with patch.object(db, "scalar", return_value=0), pytest.raises(ErrorApi) as error:
        catalogos.borrar_colonia(db, colonia_id)
    assert error.value.status_code == 409 and error.value.codigo == "COLONIA_CON_REPORTES"
    assert db.get(Colonia, colonia_id) is not None  # se deshizo el borrado


# --- Sectores --------------------------------------------------------------------------------------
def test_alta_y_renombrado_de_sector(client, admin):
    r = client.post("/api/sectores", json={"nombre": " Sector  Nuevo "}, headers=admin)
    assert r.status_code == 201
    assert set(r.json()) == {"id", "nombre"} and r.json()["nombre"] == "Sector Nuevo"
    r = client.put(f"/api/sectores/{r.json()['id']}", json={"nombre": "Sector Renombrado"}, headers=admin)
    assert r.status_code == 200 and r.json()["nombre"] == "Sector Renombrado"
    assert "Sector Renombrado" in [s["nombre"] for s in client.get("/api/sectores").json()]


def test_sector_con_nombre_repetido_da_409(client, admin, catalogo):
    r = client.post("/api/sectores", json={"nombre": "CENTRO"}, headers=admin)
    assert r.status_code == 409 and r.json()["codigo"] == "SECTOR_DUPLICADO"
    otro = client.post("/api/sectores", json={"nombre": "Otro"}, headers=admin).json()
    r = client.put(f"/api/sectores/{otro['id']}", json={"nombre": "Centro"}, headers=admin)
    assert r.status_code == 409
    # Conservar el propio nombre no es duplicado
    assert client.put(f"/api/sectores/{otro['id']}", json={"nombre": "Otro"}, headers=admin).status_code == 200


def test_sector_datos_invalidos_y_inexistente(client, admin):
    r = client.post("/api/sectores", json={"nombre": "x"}, headers=admin)
    assert r.status_code == 422 and "nombre" in r.json()["campos"]
    assert client.post("/api/sectores", json={"nombre": "S" * 81}, headers=admin).status_code == 422
    assert client.put("/api/sectores/9999", json={"nombre": "Algo"}, headers=admin).status_code == 404


def test_la_restriccion_de_la_base_tambien_protege(db, catalogo):
    """Si dos peticiones pasan la revisión a la vez, la restricción única de la base responde 409 (IntegrityError)."""
    from unittest.mock import patch

    from app.core.errores import ErrorApi
    from app.schemas.catalogos import ColoniaEntrada
    from app.services import catalogos

    datos = ColoniaEntrada(nombre="Partido Escobedo", sector_id=catalogo["sector"].id)
    with patch.object(catalogos, "_revisar_nombre_de_colonia"), pytest.raises(ErrorApi) as error:
        catalogos.crear_colonia(db, datos)
    assert error.value.status_code == 409 and error.value.codigo == "COLONIA_DUPLICADA"


# --- Roles -----------------------------------------------------------------------------------------
RUTAS = [
    ("post", "/api/colonias", {"nombre": "Colonia X", "sector_id": 1}),
    ("put", "/api/colonias/1", {"nombre": "Colonia X", "sector_id": 1, "activa": True}),
    ("delete", "/api/colonias/1", None),
    ("post", "/api/sectores", {"nombre": "Sector X"}),
    ("put", "/api/sectores/1", {"nombre": "Sector X"}),
]


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo"), RUTAS)
def test_sin_token_da_401(client, catalogo, metodo, ruta, cuerpo):
    r = getattr(client, metodo)(ruta, **({"json": cuerpo} if cuerpo else {}))
    assert r.status_code == 401 and r.json()["codigo"] == "NO_AUTENTICADO"


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo"), RUTAS)
@pytest.mark.parametrize("rol", ["ciudadano", "moderador"])
def test_otros_roles_dan_403_y_no_cambian_nada(client, db, catalogo, crear_usuario, metodo, ruta, cuerpo, rol):
    usuario = crear_usuario(f"{rol}-x@ejemplo.test", rol=rol)
    antes = db.scalar(select(func.count()).select_from(Colonia)), db.scalar(select(func.count()).select_from(Sector))
    r = getattr(client, metodo)(ruta, headers=encabezado_de(usuario), **({"json": cuerpo} if cuerpo else {}))
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    despues = db.scalar(select(func.count()).select_from(Colonia)), db.scalar(select(func.count()).select_from(Sector))
    assert antes == despues


def test_la_lectura_publica_sigue_abierta(client, catalogo):
    assert client.get("/api/colonias").status_code == 200
    assert client.get("/api/sectores").status_code == 200


def test_coordinador_suspendido_ya_no_administra(client, db, coordinador, datos_nueva):
    usuario = db.get(Usuario, coordinador.id)
    usuario.activo = False
    db.commit()
    r = client.post("/api/colonias", json=datos_nueva, headers=encabezado_de(coordinador))
    assert r.status_code == 403 and r.json()["codigo"] == "CUENTA_SUSPENDIDA"
