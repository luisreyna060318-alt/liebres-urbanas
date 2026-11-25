"""Autorización en el servidor: require_role y rol leído de la base en cada petición (HU-01.3, HU-06.2 CA2)."""

import pytest

from tests.conftest import encabezado_de

# (ruta de prueba, roles que pueden entrar)
MATRIZ = [
    ("/api/_pruebas/solo-coordinador", {"coordinador"}),
    ("/api/_pruebas/moderacion", {"moderador", "coordinador"}),
    ("/api/_pruebas/solo-ciudadano", {"ciudadano"}),
]
ROLES = ["ciudadano", "moderador", "coordinador"]


@pytest.mark.parametrize("ruta,permitidos", MATRIZ)
@pytest.mark.parametrize("rol", ROLES)
def test_matriz_rol_por_ruta(client, crear_usuario, ruta, permitidos, rol):
    usuario = crear_usuario(f"{rol}@ejemplo.test", rol=rol)
    r = client.get(ruta, headers=encabezado_de(usuario))
    if rol in permitidos:
        assert r.status_code == 200 and r.json() == {"rol": rol}
    else:
        assert r.status_code == 403
        assert r.json()["codigo"] == "SIN_PERMISO"


@pytest.mark.parametrize("ruta,_permitidos", MATRIZ)
def test_ruta_protegida_sin_sesion_responde_401(client, ruta, _permitidos):
    r = client.get(ruta)
    assert r.status_code == 401 and r.json()["codigo"] == "NO_AUTENTICADO"


def test_el_rol_se_lee_de_la_base_en_cada_peticion(client, db, ciudadano):
    """Con el MISMO token, un cambio de rol surte efecto en la siguiente petición."""
    cabecera = encabezado_de(ciudadano)
    assert client.get("/api/_pruebas/solo-coordinador", headers=cabecera).status_code == 403

    ciudadano.rol = "coordinador"
    db.commit()
    assert client.get("/api/_pruebas/solo-coordinador", headers=cabecera).status_code == 200
    assert client.get("/api/auth/yo", headers=cabecera).json()["rol"] == "coordinador"

    ciudadano.rol = "ciudadano"
    db.commit()
    assert client.get("/api/_pruebas/solo-coordinador", headers=cabecera).status_code == 403


def test_suspender_surte_efecto_en_la_siguiente_peticion(client, db, moderador):
    cabecera = encabezado_de(moderador)
    assert client.get("/api/_pruebas/moderacion", headers=cabecera).status_code == 200
    moderador.activo = False
    db.commit()
    r = client.get("/api/_pruebas/moderacion", headers=cabecera)
    assert r.status_code == 403 and r.json()["codigo"] == "CUENTA_SUSPENDIDA"


def test_token_de_usuario_inexistente_responde_401(client, db, ciudadano):
    cabecera = encabezado_de(ciudadano)
    db.delete(ciudadano)
    db.commit()
    assert client.get("/api/auth/yo", headers=cabecera).status_code == 401
