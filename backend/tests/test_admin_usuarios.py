"""Administración de usuarios y roles (HU-06.2): solo coordinador."""

import pytest
from sqlalchemy import func, select

from app.models import Reporte, Usuario
from tests.conftest import PASSWORD_PRUEBA, encabezado_de, llaves_de


@pytest.fixture()
def admin(coordinador):
    return encabezado_de(coordinador)


@pytest.fixture()
def gente(crear_usuario):
    """Cuentas ficticias para buscar y filtrar."""
    return {
        "ana": crear_usuario("ana.perez@ejemplo.test", nombre="Ana Pérez"),
        "luis": crear_usuario("luis@ejemplo.test", nombre="Luis Ríos", rol="moderador"),
        "marta": crear_usuario("marta@ejemplo.test", nombre="Marta Soto", activo=False),
    }


# --- Listado, búsqueda y filtro ---------------------------------------------------------------------
def test_listado_con_la_forma_del_contrato_y_sin_hash(client, admin, gente):
    r = client.get("/api/usuarios", headers=admin)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["total"] == 4 and cuerpo["pagina"] == 1 and cuerpo["tam"] == 10  # 3 + el coordinador
    assert set(cuerpo["items"][0]) == {"id", "nombre", "correo", "rol", "activo", "creado_en"}
    assert cuerpo["items"][0]["creado_en"].endswith("Z")
    nombres = [u["nombre"] for u in cuerpo["items"]]
    assert nombres == sorted(nombres, key=str.lower)
    # El hash y la contraseña nunca salen
    assert not {"password", "password_hash"} & llaves_de(cuerpo)
    assert "$2b$" not in r.text and PASSWORD_PRUEBA not in r.text


def test_busqueda_por_nombre_o_correo_sin_distinguir_mayusculas(client, admin, gente):
    por_nombre = client.get("/api/usuarios?q=PÉREZ", headers=admin).json()
    assert [u["correo"] for u in por_nombre["items"]] == ["ana.perez@ejemplo.test"]
    por_correo = client.get("/api/usuarios?q=LUIS@Ejemplo", headers=admin).json()
    assert [u["nombre"] for u in por_correo["items"]] == ["Luis Ríos"]
    vacio = client.get("/api/usuarios?q=nadie", headers=admin).json()
    assert vacio == {"items": [], "total": 0, "pagina": 1, "tam": 10}


def test_la_busqueda_trata_el_porcentaje_como_texto(client, admin, gente):
    assert client.get("/api/usuarios?q=%25", headers=admin).json()["total"] == 0


def test_filtro_por_rol(client, admin, gente):
    moderadores = client.get("/api/usuarios?rol=moderador", headers=admin).json()
    assert [u["nombre"] for u in moderadores["items"]] == ["Luis Ríos"]
    assert client.get("/api/usuarios?rol=coordinador", headers=admin).json()["total"] == 1
    r = client.get("/api/usuarios?rol=jefe", headers=admin)
    assert r.status_code == 422 and "rol" in r.json()["campos"]


def test_paginacion_de_10_en_10(client, admin, crear_usuario):
    for n in range(12):
        crear_usuario(f"persona{n:02d}@ejemplo.test", nombre=f"Persona {n:02d}")
    primera = client.get("/api/usuarios", headers=admin).json()
    assert primera["total"] == 13 and len(primera["items"]) == 10
    assert len(client.get("/api/usuarios?pagina=2", headers=admin).json()["items"]) == 3


@pytest.mark.parametrize("consulta", ["tam=0", "tam=101", "pagina=0"])
def test_parametros_invalidos(client, admin, consulta):
    assert client.get(f"/api/usuarios?{consulta}", headers=admin).status_code == 422


# --- Cambio de rol ---------------------------------------------------------------------------------
def test_cambiar_rol(client, db, admin, gente):
    r = client.put(f"/api/usuarios/{gente['ana'].id}/rol", json={"rol": "moderador"}, headers=admin)
    assert r.status_code == 200
    assert r.json()["rol"] == "moderador" and r.json()["correo"] == "ana.perez@ejemplo.test"
    assert not {"password", "password_hash"} & llaves_de(r.json())
    db.refresh(gente["ana"])
    assert gente["ana"].rol == "moderador"


@pytest.mark.parametrize("cuerpo", [{"rol": "jefe"}, {"rol": ""}, {}, {"rol": None}])
def test_rol_invalido_da_422(client, admin, gente, cuerpo):
    r = client.put(f"/api/usuarios/{gente['ana'].id}/rol", json=cuerpo, headers=admin)
    assert r.status_code == 422 and "rol" in r.json()["campos"]


def test_el_cambio_de_rol_surte_efecto_en_la_siguiente_peticion_con_el_mismo_token(client, admin, gente):
    """HU-06.2 CA2: no se espera a que el token venza."""
    luis = gente["luis"]
    token_de_luis = encabezado_de(luis)
    assert client.get("/api/_pruebas/moderacion", headers=token_de_luis).status_code == 200
    assert client.get("/api/usuarios", headers=token_de_luis).status_code == 403
    client.put(f"/api/usuarios/{luis.id}/rol", json={"rol": "ciudadano"}, headers=admin)
    assert client.get("/api/_pruebas/moderacion", headers=token_de_luis).status_code == 403  # perdió el permiso
    client.put(f"/api/usuarios/{luis.id}/rol", json={"rol": "coordinador"}, headers=admin)
    assert client.get("/api/usuarios", headers=token_de_luis).status_code == 200  # y lo recuperó, con el mismo token


def test_un_coordinador_puede_dejar_su_rol_si_hay_otro(client, db, admin, coordinador, crear_usuario):
    otro = crear_usuario("otro-coordinador@ejemplo.test", rol="coordinador")
    r = client.put(f"/api/usuarios/{coordinador.id}/rol", json={"rol": "ciudadano"}, headers=encabezado_de(otro))
    assert r.status_code == 200
    assert db.get(Usuario, coordinador.id).rol == "ciudadano"


# --- Suspensión ------------------------------------------------------------------------------------
def test_suspender_y_reactivar(client, db, admin, gente):
    ana = gente["ana"]
    r = client.put(f"/api/usuarios/{ana.id}/suspension", json={"suspendido": True}, headers=admin)
    assert r.status_code == 200 and r.json()["activo"] is False
    r = client.put(f"/api/usuarios/{ana.id}/suspension", json={"suspendido": False}, headers=admin)
    assert r.status_code == 200 and r.json()["activo"] is True
    db.refresh(ana)
    assert ana.activo is True


def test_suspension_exige_un_booleano(client, admin, gente):
    ruta = f"/api/usuarios/{gente['ana'].id}/suspension"
    assert client.put(ruta, json={}, headers=admin).status_code == 422
    r = client.put(ruta, json={"suspendido": "quizá"}, headers=admin)
    assert r.status_code == 422 and "suspendido" in r.json()["campos"]


def test_suspender_bloquea_el_login_y_el_token_vigente_y_conserva_los_reportes(
    client, db, admin, ciudadano, crear_reporte
):
    crear_reporte("bache")
    token = encabezado_de(ciudadano)
    assert client.get("/api/mis-reportes", headers=token).status_code == 200

    client.put(f"/api/usuarios/{ciudadano.id}/suspension", json={"suspendido": True}, headers=admin)

    # Con el token que ya tenía: 403 en la siguiente petición
    r = client.get("/api/mis-reportes", headers=token)
    assert r.status_code == 403 and r.json()["codigo"] == "CUENTA_SUSPENDIDA"
    # Y no puede iniciar sesión de nuevo
    r = client.post("/api/auth/login", json={"correo": ciudadano.correo, "password": PASSWORD_PRUEBA})
    assert r.status_code == 403 and r.json()["codigo"] == "CUENTA_SUSPENDIDA"
    # Sus reportes siguen ahí
    assert db.scalar(select(func.count()).select_from(Reporte).where(Reporte.autor_id == ciudadano.id)) == 1

    # Al reactivarla vuelve a entrar con la misma contraseña
    client.put(f"/api/usuarios/{ciudadano.id}/suspension", json={"suspendido": False}, headers=admin)
    r = client.post("/api/auth/login", json={"correo": ciudadano.correo, "password": PASSWORD_PRUEBA})
    assert r.status_code == 200
    assert client.get("/api/mis-reportes", headers=token).status_code == 200


# --- Último coordinador ----------------------------------------------------------------------------
def test_no_se_quita_el_rol_al_ultimo_coordinador(client, db, admin, coordinador):
    r = client.put(f"/api/usuarios/{coordinador.id}/rol", json={"rol": "ciudadano"}, headers=admin)
    assert r.status_code == 409 and r.json()["codigo"] == "ULTIMO_COORDINADOR"
    assert "último coordinador" in r.json()["detail"]
    assert db.get(Usuario, coordinador.id).rol == "coordinador"


def test_no_se_suspende_al_ultimo_coordinador_ni_a_si_mismo(client, db, admin, coordinador):
    r = client.put(f"/api/usuarios/{coordinador.id}/suspension", json={"suspendido": True}, headers=admin)
    assert r.status_code == 409 and r.json()["codigo"] == "ULTIMO_COORDINADOR"
    assert db.get(Usuario, coordinador.id).activo is True
    # Sigue con acceso
    assert client.get("/api/usuarios", headers=admin).status_code == 200


def test_poner_el_mismo_rol_al_ultimo_coordinador_no_es_un_problema(client, admin, coordinador):
    r = client.put(f"/api/usuarios/{coordinador.id}/rol", json={"rol": "coordinador"}, headers=admin)
    assert r.status_code == 200


def test_un_coordinador_suspendido_no_cuenta_como_otro(client, db, admin, coordinador, crear_usuario):
    """Con dos coordinadores donde uno ya está suspendido, el activo es el último y queda protegido."""
    crear_usuario("coordinador-suspendido@ejemplo.test", rol="coordinador", activo=False)
    r = client.put(f"/api/usuarios/{coordinador.id}/rol", json={"rol": "moderador"}, headers=admin)
    assert r.status_code == 409


def test_con_dos_coordinadores_activos_se_puede_suspender_a_uno_pero_no_al_otro(client, db, coordinador, crear_usuario):
    otro = crear_usuario("coordinador2@ejemplo.test", rol="coordinador")
    r = client.put(f"/api/usuarios/{otro.id}/suspension", json={"suspendido": True}, headers=encabezado_de(coordinador))
    assert r.status_code == 200
    r = client.put(
        f"/api/usuarios/{coordinador.id}/suspension", json={"suspendido": True}, headers=encabezado_de(coordinador)
    )
    assert r.status_code == 409 and r.json()["codigo"] == "ULTIMO_COORDINADOR"


def test_suspender_a_un_coordinador_ya_suspendido_o_reactivarlo_no_se_bloquea(client, db, admin, crear_usuario):
    suspendido = crear_usuario("coordinador-baja@ejemplo.test", rol="coordinador", activo=False)
    ruta = f"/api/usuarios/{suspendido.id}/suspension"
    assert client.put(ruta, json={"suspendido": True}, headers=admin).status_code == 200
    assert client.put(ruta, json={"suspendido": False}, headers=admin).status_code == 200


def test_cuenta_inexistente_da_404(client, admin):
    assert client.put("/api/usuarios/9999/rol", json={"rol": "ciudadano"}, headers=admin).status_code == 404
    r = client.put("/api/usuarios/9999/suspension", json={"suspendido": True}, headers=admin)
    assert r.status_code == 404 and r.json()["codigo"] == "NO_ENCONTRADO"


# --- Roles -----------------------------------------------------------------------------------------
RUTAS = [
    ("get", "/api/usuarios", None),
    ("put", "/api/usuarios/1/rol", {"rol": "moderador"}),
    ("put", "/api/usuarios/1/suspension", {"suspendido": True}),
]


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo"), RUTAS)
def test_sin_token_da_401(client, metodo, ruta, cuerpo):
    r = getattr(client, metodo)(ruta, **({"json": cuerpo} if cuerpo else {}))
    assert r.status_code == 401 and r.json()["codigo"] == "NO_AUTENTICADO"


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo"), RUTAS)
@pytest.mark.parametrize("rol", ["ciudadano", "moderador"])
def test_otros_roles_dan_403_y_no_cambian_nada(client, db, crear_usuario, metodo, ruta, cuerpo, rol):
    usuario = crear_usuario(f"{rol}-x@ejemplo.test", rol=rol)
    objetivo = crear_usuario("objetivo@ejemplo.test")  # id distinto de 1 no importa: el 403 llega antes que el 404
    r = getattr(client, metodo)(ruta, headers=encabezado_de(usuario), **({"json": cuerpo} if cuerpo else {}))
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    db.refresh(usuario)
    db.refresh(objetivo)
    assert usuario.rol == rol and usuario.activo and objetivo.rol == "ciudadano" and objetivo.activo


def test_un_moderador_no_puede_ascenderse_a_si_mismo(client, db, moderador):
    r = client.put(f"/api/usuarios/{moderador.id}/rol", json={"rol": "coordinador"}, headers=encabezado_de(moderador))
    assert r.status_code == 403
    assert db.get(Usuario, moderador.id).rol == "moderador"
