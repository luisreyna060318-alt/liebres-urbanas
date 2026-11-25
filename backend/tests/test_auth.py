"""Registro, login, refresh y sesión (HU-01.1, HU-01.2)."""

from datetime import timedelta

import jwt
import pytest

from app.models import Usuario
from tests.conftest import PASSWORD_PRUEBA, encabezado_de

REGISTRO_OK = {"nombre": "Ana Pérez", "correo": "ana@ejemplo.test", "password": "Clave1234", "acepta_privacidad": True}


def registrar(client, **cambios):
    return client.post("/api/auth/registro", json={**REGISTRO_OK, **cambios})


# --- HU-01.1 Crear una cuenta ---------------------------------------------------------------------
def test_registro_crea_ciudadano_y_deja_la_sesion_abierta(client, db):
    """CA1: rol ciudadano por omisión y la persona queda dentro."""
    r = registrar(client, correo="  Ana@Ejemplo.TEST ")
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["token_type"] == "bearer"
    assert cuerpo["expira_en_min"] == 30
    assert cuerpo["usuario"] == {"id": cuerpo["usuario"]["id"], "nombre": "Ana Pérez",
                                 "correo": "ana@ejemplo.test", "rol": "ciudadano"}
    # El token sirve de inmediato
    yo = client.get("/api/auth/yo", headers={"Authorization": f"Bearer {cuerpo['access_token']}"})
    assert yo.status_code == 200 and yo.json()["rol"] == "ciudadano"
    usuario = db.get(Usuario, cuerpo["usuario"]["id"])
    assert usuario.acepto_privacidad_en is not None


def test_registro_no_permite_elegir_rol(client):
    r = registrar(client, rol="coordinador")
    assert r.status_code == 201
    assert r.json()["usuario"]["rol"] == "ciudadano"


@pytest.mark.parametrize("correo", ["ana@ejemplo.test", "ANA@EJEMPLO.TEST", " Ana@Ejemplo.test "])
def test_registro_correo_duplicado_sin_importar_mayusculas(client, correo):
    """CA2: el mismo correo con otras mayúsculas o espacios es la misma cuenta."""
    assert registrar(client).status_code == 201
    r = registrar(client, correo=correo)
    assert r.status_code == 409
    assert r.json()["codigo"] == "CORREO_REGISTRADO"


@pytest.mark.parametrize("password", ["corta1", "sololetrasaqui", "1234567890", ""])
def test_registro_contrasena_debil_con_error_en_el_campo(client, password):
    """CA3: el error va junto al campo password."""
    r = registrar(client, password=password)
    assert r.status_code == 422
    cuerpo = r.json()
    assert cuerpo["codigo"] == "VALIDACION"
    assert list(cuerpo["campos"]) == ["password"]
    assert "letras y números" in cuerpo["campos"]["password"]


@pytest.mark.parametrize("valor", [False, None, "omitido"])
def test_registro_sin_aceptar_aviso_de_privacidad(client, valor):
    """CA4: sin aceptación (false, nulo o ausente) no hay cuenta."""
    datos = {**REGISTRO_OK}
    if valor == "omitido":
        del datos["acepta_privacidad"]
    else:
        datos["acepta_privacidad"] = valor
    r = client.post("/api/auth/registro", json=datos)
    assert r.status_code == 422
    assert "acepta_privacidad" in r.json()["campos"]


def test_registro_varios_campos_invalidos_a_la_vez(client):
    r = client.post("/api/auth/registro", json={"nombre": "A", "correo": "no-es-correo", "password": "x"})
    assert r.status_code == 422
    campos = r.json()["campos"]
    assert set(campos) == {"nombre", "correo", "password", "acepta_privacidad"}
    assert "correo" in campos["correo"].lower()


# --- HU-01.2 Iniciar sesión -----------------------------------------------------------------------
def test_login_correcto_sin_importar_mayusculas(client, ciudadano):
    r = client.post("/api/auth/login", json={"correo": " CIUDADANO@ejemplo.test", "password": PASSWORD_PRUEBA})
    assert r.status_code == 200
    assert r.json()["usuario"]["id"] == ciudadano.id
    assert r.json()["expira_en_min"] == 30


def test_login_mensaje_unico_para_correo_o_contrasena(client, ciudadano):
    """CA2: no se revela si falló el correo o la contraseña."""
    mala_clave = client.post("/api/auth/login", json={"correo": ciudadano.correo, "password": "Otra12345"})
    sin_cuenta = client.post("/api/auth/login", json={"correo": "nadie@ejemplo.test", "password": PASSWORD_PRUEBA})
    assert mala_clave.status_code == sin_cuenta.status_code == 401
    esperado = {"detail": "Correo o contraseña incorrectos", "codigo": "CREDENCIALES"}
    assert mala_clave.json() == sin_cuenta.json() == esperado


def test_cuenta_suspendida_no_entra_ni_usa_su_token(client, crear_usuario):
    suspendida = crear_usuario("suspendida@ejemplo.test", activo=False)
    r = client.post("/api/auth/login", json={"correo": suspendida.correo, "password": PASSWORD_PRUEBA})
    assert r.status_code == 403 and r.json()["codigo"] == "CUENTA_SUSPENDIDA"
    # Un token emitido antes de la suspensión deja de servir
    r = client.get("/api/auth/yo", headers=encabezado_de(suspendida))
    assert r.status_code == 403 and r.json()["codigo"] == "CUENTA_SUSPENDIDA"


@pytest.mark.parametrize(
    "encabezados",
    [
        {},
        {"Authorization": "Bearer esto-no-es-un-jwt"},
        {"Authorization": "Basic abc"},
    ],
    ids=["sin-token", "token-basura", "otro-esquema"],
)
def test_sin_token_valido_responde_401(client, encabezados):
    r = client.get("/api/auth/yo", headers=encabezados)
    assert r.status_code == 401
    assert r.json()["codigo"] == "NO_AUTENTICADO"


def test_token_vencido_responde_401(client, ciudadano):
    r = client.get("/api/auth/yo", headers=encabezado_de(ciudadano, expira_en=timedelta(seconds=-1)))
    assert r.status_code == 401
    assert r.json()["codigo"] == "NO_AUTENTICADO"
    assert r.headers["WWW-Authenticate"] == "Bearer"


def test_token_firmado_con_otra_clave_responde_401(client, ciudadano):
    falso = jwt.encode({"sub": str(ciudadano.id), "exp": 9999999999}, "otra-clave-de-alguien-mas-1234567890", "HS256")
    r = client.get("/api/auth/yo", headers={"Authorization": f"Bearer {falso}"})
    assert r.status_code == 401


def test_token_dura_30_minutos(client, ciudadano):
    r = client.post("/api/auth/login", json={"correo": ciudadano.correo, "password": PASSWORD_PRUEBA})
    datos = jwt.decode(r.json()["access_token"], options={"verify_signature": False})
    assert datos["exp"] - datos["iat"] == 30 * 60


def test_refresh_entrega_un_token_nuevo(client, ciudadano):
    r = client.post("/api/auth/refresh", headers=encabezado_de(ciudadano, expira_en=timedelta(minutes=1)))
    assert r.status_code == 200
    nuevo = r.json()["access_token"]
    datos = jwt.decode(nuevo, options={"verify_signature": False})
    assert datos["exp"] - datos["iat"] == 30 * 60
    assert client.get("/api/auth/yo", headers={"Authorization": f"Bearer {nuevo}"}).status_code == 200


def test_refresh_con_token_vencido_no_renueva(client, ciudadano):
    r = client.post("/api/auth/refresh", headers=encabezado_de(ciudadano, expira_en=timedelta(seconds=-1)))
    assert r.status_code == 401 and r.json()["codigo"] == "NO_AUTENTICADO"


def test_el_hash_nunca_aparece_en_las_respuestas(client, db):
    respuestas = [registrar(client)]
    respuestas.append(client.post("/api/auth/login", json={"correo": "ana@ejemplo.test", "password": "Clave1234"}))
    token = respuestas[-1].json()["access_token"]
    cabecera = {"Authorization": f"Bearer {token}"}
    respuestas.append(client.post("/api/auth/refresh", headers=cabecera))
    respuestas.append(client.get("/api/auth/yo", headers=cabecera))
    hash_guardado = db.query(Usuario).one().password_hash
    for r in respuestas:
        assert r.status_code in (200, 201)
        assert "password" not in r.text
        assert hash_guardado not in r.text
