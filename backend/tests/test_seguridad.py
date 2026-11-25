"""Seguridad del backend: matriz rol x endpoint (HU-01.3), autoría, privacidad (RN-04) y contraseñas (RNF-05).

La matriz recorre TODOS los endpoints que existen hoy. Si agregas uno, agrégalo a ENDPOINTS: la prueba
test_la_matriz_cubre_todas_las_rutas falla si una ruta de la aplicación no está en la lista.
"""

from datetime import timedelta

import pytest

from app.main import app
from app.models import Reporte
from app.schemas.geo import GeoBusqueda, GeoResultado
from app.schemas.reportes import CambioEstado, Cercano, ReporteDetalle, ReporteMio, ReportePublico
from app.services import geocodificacion
from tests.conftest import HASH_PRUEBA, LLAVES_PROHIBIDAS, datos_bache, encabezado_de, llaves_de, punto

ROLES = ("ciudadano", "moderador", "coordinador")
SOLO_CIUDADANO = {"ciudadano"}
CUALQUIER_ROL = set(ROLES)
PUBLICO = None  # sin sesión


def _cuerpo_encharcamiento(colonia_id: int) -> dict:
    lat, lon = punto(30)
    return {"lat": lat, "lon": lon, "calle": "Calle", "colonia_id": colonia_id, "nivel_agua": "a_un_lado"}


def _cuerpo_edicion(colonia_id: int) -> dict:
    datos = datos_bache(colonia_id, 0)
    datos.pop("forzar")
    return datos


# (método, ruta con {ajeno}/{propio}, función que arma el cuerpo con el escenario, quién puede entrar)
# {ajeno} = bache de OTRA persona (para confirmar); {propio} = bache del usuario de la prueba (editar/borrar)
ENDPOINTS = [
    ("GET", "/api/health", None, PUBLICO),
    ("GET", "/api/reglas", None, PUBLICO),
    ("GET", "/api/sectores", None, PUBLICO),
    ("GET", "/api/colonias", None, PUBLICO),
    ("GET", "/api/tipos-dano", None, PUBLICO),
    ("GET", "/api/motivos-rechazo", None, PUBLICO),
    ("GET", "/api/geo/buscar?q=Av.%20Tecnologico", None, PUBLICO),
    ("GET", "/api/geo/inversa?lat=31.7&lon=-106.43", None, PUBLICO),
    ("POST", "/api/auth/refresh", None, CUALQUIER_ROL),
    ("GET", "/api/auth/yo", None, CUALQUIER_ROL),
    ("POST", "/api/reportes/baches", lambda e: datos_bache(e["colonia_id"], 20), SOLO_CIUDADANO),
    ("POST", "/api/reportes/encharcamientos", lambda e: _cuerpo_encharcamiento(e["colonia_id"]), SOLO_CIUDADANO),
    ("GET", "/api/reportes/cercanos?categoria=bache&lat=31.7&lon=-106.43", None, SOLO_CIUDADANO),
    ("POST", "/api/reportes/{ajeno}/confirmaciones", lambda e: {"tipo": "confirma"}, SOLO_CIUDADANO),
    ("GET", "/api/mis-reportes", None, SOLO_CIUDADANO),
    ("PUT", "/api/reportes/{propio}", lambda e: _cuerpo_edicion(e["colonia_id"]), SOLO_CIUDADANO),
    ("DELETE", "/api/reportes/{propio}", None, SOLO_CIUDADANO),
]
# Administración de usuarios (HU-06.2): su matriz de roles está en test_admin_usuarios.py
RUTAS_ADMIN_USUARIOS = {
    ("GET", "/api/usuarios"),
    ("PUT", "/api/usuarios/{usuario_id}/rol"),
    ("PUT", "/api/usuarios/{usuario_id}/suspension"),
}
# Registro y login son públicos pero se prueban aparte (crean cuentas y necesitan credenciales)
RUTAS_PROBADAS_APARTE = {("POST", "/api/auth/registro"), ("POST", "/api/auth/login")}


@pytest.fixture(autouse=True)
def nominatim_falso(monkeypatch):
    monkeypatch.setattr(geocodificacion, "_llamar_http", lambda ruta, parametros: [] if ruta == "search" else {})


@pytest.fixture()
def escenario(db, crear_usuario, catalogo):
    """Fábrica: para un usuario dado, crea un bache SUYO y uno de otra persona. Devuelve los ids y la colonia."""
    autora = crear_usuario("autora@ejemplo.test")

    def _bache(autor_id: int, n: int) -> int:
        lat, lon = punto(n)
        reporte = Reporte(folio=f"BCH-1999-{n:06d}", categoria="bache", tipo_dano_id=catalogo["tipos"]["bache"].id,
                          autor_id=autor_id, colonia_id=catalogo["colonia"].id, calle="Calle", lat=lat, lon=lon,
                          severidad="baja", tamano="chico", profundidad="baja", carril="orilla", estado="recibido")
        db.add(reporte)
        db.commit()
        return reporte.id

    def _armar(usuario) -> dict:
        return {"ajeno": _bache(autora.id, 1), "propio": _bache(usuario.id, 2) if usuario else _bache(autora.id, 2),
                "colonia_id": catalogo["colonia"].id}

    return _armar


def _llamar(client, metodo, ruta, cuerpo, escenario, headers):
    ruta = ruta.format(ajeno=escenario["ajeno"], propio=escenario["propio"])
    return client.request(metodo, ruta, json=cuerpo(escenario) if cuerpo else None, headers=headers)


def _id_caso(endpoint):
    return f"{endpoint[0]} {endpoint[1].split('?')[0]}"


# --- Matriz rol x endpoint -------------------------------------------------------------------------
@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=_id_caso)
def test_sin_token(client, escenario, endpoint):
    metodo, ruta, cuerpo, permitidos = endpoint
    r = _llamar(client, metodo, ruta, cuerpo, escenario(None), headers={})
    if permitidos is PUBLICO:
        assert r.status_code == 200, r.text
    else:
        assert r.status_code == 401 and r.json()["codigo"] == "NO_AUTENTICADO"
        assert r.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("rol", ROLES)
@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=_id_caso)
def test_matriz_rol_por_endpoint(client, crear_usuario, escenario, endpoint, rol):
    metodo, ruta, cuerpo, permitidos = endpoint
    usuario = crear_usuario(f"{rol}@ejemplo.test", rol=rol)
    r = _llamar(client, metodo, ruta, cuerpo, escenario(usuario), headers=encabezado_de(usuario))
    if permitidos is PUBLICO or rol in permitidos:
        assert r.status_code in (200, 201, 204), r.text
    else:
        assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"


def test_la_matriz_cubre_todas_las_rutas():
    """Ninguna ruta de la API queda fuera de la matriz (las de /api/_pruebas solo existen en las pruebas)."""
    en_matriz = {(m, r.split("?")[0].replace("{ajeno}", "{reporte_id}").replace("{propio}", "{reporte_id}"))
                 for m, r, _, _ in ENDPOINTS}
    # Se leen de la documentación OpenAPI, que lista cada ruta con sus métodos
    en_app = {
        (metodo.upper(), ruta)
        for ruta, metodos in app.openapi()["paths"].items()
        if ruta.startswith("/api") and not ruta.startswith("/api/_pruebas")
        for metodo in metodos
    }
    assert en_app - RUTAS_PROBADAS_APARTE - RUTAS_ADMIN_USUARIOS == en_matriz


@pytest.mark.parametrize("rol", ["moderador", "coordinador"])
def test_el_403_llega_antes_que_la_validacion_del_cuerpo(client, crear_usuario, rol):
    """Un rol sin permiso recibe 403 aunque el cuerpo esté mal: no se le da información sobre los campos."""
    usuario = crear_usuario(f"{rol}@ejemplo.test", rol=rol)
    r = client.post("/api/reportes/baches", json={"lat": "no"}, headers=encabezado_de(usuario))
    assert r.status_code == 403


def test_token_vencido_o_alterado_responde_401(client, ciudadano, catalogo):
    vencido = encabezado_de(ciudadano, expira_en=timedelta(seconds=-1))
    assert client.post("/api/reportes/baches", json=datos_bache(catalogo["colonia"].id), headers=vencido).status_code \
        == 401
    token = encabezado_de(ciudadano)["Authorization"]
    alterado = {"Authorization": token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")}
    assert client.get("/api/mis-reportes", headers=alterado).status_code == 401


# --- Suspensión y cambio de rol con un token todavía vigente ----------------------------------------
def test_suspendido_recibe_403_de_inmediato(client, db, ciudadano, catalogo):
    token = encabezado_de(ciudadano)
    assert client.get("/api/mis-reportes", headers=token).status_code == 200
    ciudadano.activo = False
    db.commit()
    for metodo, ruta, cuerpo in [
        ("GET", "/api/mis-reportes", None),
        ("POST", "/api/reportes/baches", datos_bache(catalogo["colonia"].id)),
        ("POST", "/api/auth/refresh", None),
    ]:
        r = client.request(metodo, ruta, json=cuerpo, headers=token)
        assert r.status_code == 403 and r.json()["codigo"] == "CUENTA_SUSPENDIDA"


def test_el_cambio_de_rol_surte_efecto_en_la_siguiente_peticion(client, db, ciudadano, catalogo):
    token = encabezado_de(ciudadano)
    assert client.post("/api/reportes/baches", json=datos_bache(catalogo["colonia"].id, 1), headers=token).status_code \
        == 201
    ciudadano.rol = "moderador"
    db.commit()
    r = client.post("/api/reportes/baches", json=datos_bache(catalogo["colonia"].id, 2), headers=token)
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    ciudadano.rol = "ciudadano"
    db.commit()
    assert client.post("/api/reportes/baches", json=datos_bache(catalogo["colonia"].id, 3), headers=token).status_code \
        == 201


# --- Autoría (HU-01.3 CA3) -----------------------------------------------------------------------
def test_otro_ciudadano_no_edita_ni_borra(client, db, crear_usuario, escenario):
    intrusa = crear_usuario("intrusa@ejemplo.test")
    ids = escenario(None)  # los dos baches son de "autora"
    r = client.put(f"/api/reportes/{ids['propio']}", json=_cuerpo_edicion(ids["colonia_id"]),
                   headers=encabezado_de(intrusa))
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"
    r = client.delete(f"/api/reportes/{ids['propio']}", headers=encabezado_de(intrusa))
    assert r.status_code == 403
    assert db.get(Reporte, ids["propio"]) is not None


# --- Privacidad (RN-04) y contraseñas (RNF-05) -----------------------------------------------------
ESQUEMAS_PUBLICOS = [ReportePublico, ReporteMio, Cercano, ReporteDetalle, CambioEstado, GeoResultado, GeoBusqueda]


@pytest.mark.parametrize("esquema", ESQUEMAS_PUBLICOS, ids=lambda e: e.__name__)
def test_ningun_esquema_publico_tiene_datos_del_autor(esquema):
    """Revisa los campos del esquema y de sus esquemas anidados (tal como salen en /docs)."""
    llaves = llaves_de(esquema.model_json_schema())
    assert not (llaves & LLAVES_PROHIBIDAS)


def test_los_esquemas_de_la_documentacion_no_tienen_datos_del_autor():
    componentes = app.openapi()["components"]["schemas"]
    for nombre, esquema in componentes.items():
        if nombre.startswith(("Usuario", "Sesion", "Registro", "Login", "Body_")):
            continue  # cuenta propia: ahí sí van nombre y correo de la persona (nunca el hash)
        assert not (set(esquema.get("properties", {})) & LLAVES_PROHIBIDAS), nombre
    assert "password_hash" not in str(componentes)


@pytest.mark.parametrize("rol", ROLES)
def test_ninguna_respuesta_trae_el_hash_ni_datos_del_autor(client, crear_usuario, escenario, rol):
    """Recorre las respuestas JSON de todos los endpoints de reportes y ubicación buscando llaves prohibidas."""
    usuario = crear_usuario(f"{rol}@ejemplo.test", rol=rol, nombre="Nombre Muy Privado")
    ids = escenario(usuario)
    for metodo, ruta, cuerpo, _ in ENDPOINTS:
        r = _llamar(client, metodo, ruta, cuerpo, ids, headers=encabezado_de(usuario))
        assert HASH_PRUEBA not in r.text and "password_hash" not in r.text
        if "/auth/" in ruta or not r.content:
            continue  # /auth/yo y /auth/refresh devuelven a la propia persona su nombre y correo (es correcto)
        assert not (llaves_de(r.json()) & LLAVES_PROHIBIDAS), ruta
        assert usuario.correo not in r.text and "Nombre Muy Privado" not in r.text, ruta


def test_el_duplicado_no_revela_al_autor_del_reporte_cercano(client, crear_usuario, escenario, catalogo):
    vecino = crear_usuario("vecino@ejemplo.test")
    escenario(None)  # bache de "autora" en punto(1)
    r = client.post("/api/reportes/baches", json=datos_bache(catalogo["colonia"].id, 1), headers=encabezado_de(vecino))
    assert r.status_code == 409
    assert not (llaves_de(r.json()) & LLAVES_PROHIBIDAS)
    assert "autora@ejemplo.test" not in r.text


def test_registro_y_login_no_devuelven_el_hash(client):
    datos = {"nombre": "Ana Pérez", "correo": "ana@ejemplo.test", "password": "Clave1234", "acepta_privacidad": True}
    registro = client.post("/api/auth/registro", json=datos)
    login = client.post("/api/auth/login", json={"correo": "ana@ejemplo.test", "password": "Clave1234"})
    for r in (registro, login):
        assert r.status_code in (200, 201)
        assert "password" not in llaves_de(r.json()) and "password_hash" not in llaves_de(r.json())
        assert "Clave1234" not in r.text and "$2b$" not in r.text


def test_cabeceras_de_seguridad_en_las_respuestas(client, ciudadano):
    r = client.get("/api/mis-reportes", headers=encabezado_de(ciudadano))
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Cache-Control"] == "no-store"


def test_hsts_solo_en_produccion(client, monkeypatch):
    from app.core.config import settings

    assert "Strict-Transport-Security" not in client.get("/api/reglas").headers
    monkeypatch.setattr(settings, "entorno", "produccion")
    assert client.get("/api/reglas").headers["Strict-Transport-Security"].startswith("max-age=")
