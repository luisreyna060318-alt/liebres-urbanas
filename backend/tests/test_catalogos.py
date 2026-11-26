"""Reglas, salud, catálogos y semilla."""

import pytest
import seed
from sqlalchemy import func, select

from app.models import Colonia, MotivoRechazo, Sector, TipoDano, Usuario
from app.services.auth import autenticar


@pytest.fixture()
def sembrado(db):
    seed.sembrar(db)
    return db


def test_health(client, monkeypatch):
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"estado": "ok", "base_de_datos": "ok", "version": "local"}


def test_health_dice_el_commit_publicado(client, monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "1a2b3c4d5e6f7a8b9c0d")
    assert client.get("/api/health").json()["version"] == "1a2b3c4"


def test_reglas_tienen_la_forma_del_contrato(client):
    r = client.get("/api/reglas")
    assert r.status_code == 200
    assert r.json() == {
        "radio_duplicado_bache_m": 30, "radio_duplicado_encharcamiento_m": 50, "vigencia_encharcamiento_horas": 6,
        "desmentidos_para_cerrar": 3, "radio_zona_km": 1, "max_reportes_por_hora": 10, "descripcion_max": 500,
        "comentario_max": 500,
        "password_min": 8, "inactividad_min": 30, "tam_pagina_consulta": 20, "tam_pagina_mis_reportes": 10,
        "umbral_lluvia_pct": 30, "zona_horaria": "America/Ciudad_Juarez",
    }


def test_reglas_exponen_el_mismo_limite_de_comentario_que_valida_la_api(client):
    """La pantalla de moderación debe usar comentario_max (no descripcion_max) para el comentario de un cambio."""
    from app.core.reglas import COMENTARIO_MAX

    assert client.get("/api/reglas").json()["comentario_max"] == COMENTARIO_MAX


def test_sectores(client, sembrado):
    r = client.get("/api/sectores")
    assert r.status_code == 200
    nombres = [s["nombre"] for s in r.json()]
    assert nombres == sorted(["Centro", "Norponiente", "Nororiente", "Surponiente", "Suroriente"])
    assert set(r.json()[0]) == {"id", "nombre"}


def test_tipos_dano_solo_activos(client, sembrado):
    sembrado.scalar(select(TipoDano).where(TipoDano.codigo == "grieta")).activo = False
    sembrado.commit()
    r = client.get("/api/tipos-dano")
    assert r.status_code == 200
    assert [t["codigo"] for t in r.json()] == ["bache", "hundimiento", "alcantarilla_sin_tapa"]
    assert set(r.json()[0]) == {"id", "codigo", "nombre"}


def test_motivos_rechazo_solo_activos_con_pide_explicacion(client, sembrado):
    sembrado.scalar(select(MotivoRechazo).where(MotivoRechazo.codigo == "duplicado")).activo = False
    sembrado.commit()
    motivos = {m["codigo"]: m for m in client.get("/api/motivos-rechazo").json()}
    assert set(motivos) == {"fuera_del_municipio", "no_es_via_publica", "contenido_inapropiado", "otro"}
    assert motivos["otro"]["pide_explicacion"] is True
    assert motivos["no_es_via_publica"]["pide_explicacion"] is False
    assert set(motivos["otro"]) == {"id", "codigo", "nombre", "pide_explicacion"}


@pytest.fixture()
def colonias(db):
    centro, norte = Sector(nombre="Centro"), Sector(nombre="Norponiente")
    db.add_all([centro, norte])
    db.flush()
    db.add_all([Colonia(nombre=f"Colonia Ficticia {n:02d}", sector_id=centro.id, lat=31.7, lon=-106.4)
                for n in range(1, 13)])
    db.add(Colonia(nombre="Barrio Inventado", sector_id=norte.id))
    db.add(Colonia(nombre="Colonia Cerrada", sector_id=norte.id, activa=False))
    db.commit()
    return {"centro": centro, "norte": norte}


def test_colonias_paginadas_con_su_sector(client, colonias):
    r = client.get("/api/colonias")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["total"] == 13 and cuerpo["pagina"] == 1 and cuerpo["tam"] == 10
    assert len(cuerpo["items"]) == 10
    primera = cuerpo["items"][0]
    assert set(primera) == {"id", "nombre", "sector", "activa", "lat", "lon"}
    assert primera["nombre"] == "Barrio Inventado" and primera["sector"]["nombre"] == "Norponiente"
    segunda = client.get("/api/colonias?pagina=2").json()
    assert len(segunda["items"]) == 3


def test_colonias_filtros(client, colonias):
    assert client.get("/api/colonias?q=barrio").json()["total"] == 1
    assert client.get(f"/api/colonias?sector_id={colonias['norte'].id}").json()["total"] == 1
    assert client.get("/api/colonias?solo_activas=false").json()["total"] == 14
    assert client.get("/api/colonias?tam=500").json()["tam"] == 500


@pytest.mark.parametrize("consulta", ["tam=501", "tam=0", "pagina=0", "sector_id=abc"])
def test_colonias_parametros_invalidos(client, consulta):
    r = client.get(f"/api/colonias?{consulta}")
    assert r.status_code == 422
    assert r.json()["codigo"] == "VALIDACION"
    assert consulta.split("=")[0] in r.json()["campos"]


def test_semilla_idempotente_y_cuentas_demo(db, monkeypatch):
    # Sin variables SEED_*_PASSWORD (aunque la laptop tenga un .env con ellas)
    for variable in ("seed_ciudadano_password", "seed_moderador_password", "seed_coordinador_password"):
        monkeypatch.setattr(seed.settings, variable, None)
    primera = seed.sembrar(db)
    assert primera == {"sectores": 5, "tipos de daño": 4, "motivos de rechazo": 5, "cuentas de demostración": 3}
    segunda = seed.sembrar(db)
    assert set(segunda.values()) == {0}
    roles = set(db.scalars(select(Usuario.rol)))
    assert roles == {"ciudadano", "moderador", "coordinador"}
    assert db.scalar(select(func.count()).select_from(Usuario).where(Usuario.correo.like("%@liebreurbana.test"))) == 3
    # En desarrollo, sin variables, la contraseña es la de demostración
    assert autenticar(db, "moderador@liebreurbana.test", seed.CONTRASENA_DEMO).rol == "moderador"
