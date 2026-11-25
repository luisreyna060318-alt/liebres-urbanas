"""Consulta pública de reportes: filtros, búsqueda, paginación y visibilidad (HU-04.1 y HU-04.2)."""

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.core.tiempo import ahora_utc
from app.models import Colonia, Reporte, Sector
from app.services.consulta import FiltroReportes, consulta_reportes
from tests.conftest import LLAVES_PROHIBIDAS, encabezado_de, llaves_de


@pytest.fixture()
def datos(db: Session, catalogo, ciudadano):
    """Fábrica de reportes insertados directo en la base, con folio consecutivo y una segunda colonia en otro sector."""
    otro_sector = Sector(nombre="Sur")
    db.add(otro_sector)
    db.flush()
    lejana = Colonia(nombre="Colonia Lejana", sector_id=otro_sector.id)
    db.add(lejana)
    db.commit()
    contador = {"n": 0}
    base = datetime(2026, 11, 20, 18, 0, tzinfo=UTC)

    def _crear(categoria="bache", estado=None, calle="Calle Ficticia", colonia=None, creado_en=None,
               severidad="baja", **extra):
        contador["n"] += 1
        n = contador["n"]
        comunes = dict(
            autor_id=ciudadano.id, colonia_id=(colonia or catalogo["colonia"]).id, calle=calle, lat=31.7, lon=-106.43,
            creado_en=creado_en or base + timedelta(minutes=n),
        )
        if categoria == "bache":
            estado = estado or "recibido"
            reporte = Reporte(
                folio=f"BCH-2026-{n:06d}", categoria="bache", tipo_dano_id=catalogo["tipos"]["bache"].id,
                severidad=severidad, tamano="chico", profundidad="baja", carril="orilla", estado=estado,
                fecha_reparacion=date(2026, 11, 22) if estado == "reparado" else None, **comunes, **extra,
            )
        else:
            reporte = Reporte(
                folio=f"ENC-2026-{n:06d}", categoria="encharcamiento", nivel_agua="cubre_carril",
                vigente_hasta=extra.pop("vigente_hasta", ahora_utc() + timedelta(hours=6)),
                estado=estado or "activo", **comunes, **extra,
            )
        db.add(reporte)
        db.commit()
        return reporte

    _crear.lejana = lejana
    _crear.sector_lejano = otro_sector
    return _crear


def consultar(client, headers=None, **params):
    return client.get("/api/reportes", params=params, headers=headers or {})


def folios(respuesta) -> list[str]:
    assert respuesta.status_code == 200, respuesta.text
    return [i["folio"] for i in respuesta.json()["items"]]


# --- HU-04.1: activos por omisión, sin cuenta y sin autor ------------------------------------------
def test_por_omision_solo_activos_del_mas_reciente_al_mas_antiguo(client, datos):
    abiertos = [datos("bache", e).folio for e in ("recibido", "validado", "en_reparacion")]
    activo = datos("encharcamiento").folio
    for estado in ("reparado", "rechazado"):
        datos("bache", estado)
    for estado in ("historico", "rechazado"):
        datos("encharcamiento", estado)

    r = consultar(client)
    assert folios(r) == [activo, *reversed(abiertos)]
    assert r.json()["total"] == 4 and r.json()["pagina"] == 1 and r.json()["tam"] == 20


def test_la_respuesta_publica_no_trae_al_autor(client, datos, ciudadano):
    datos("bache")
    datos("encharcamiento")
    r = consultar(client)
    assert not (llaves_de(r.json()) & LLAVES_PROHIBIDAS)
    assert ciudadano.correo not in r.text and "Persona de Prueba" not in r.text
    bache = next(i for i in r.json()["items"] if i["categoria"] == "bache")
    assert bache["sin_validar"] is True and bache["tipo_dano"] == {"codigo": "bache", "nombre": "Bache"}


def test_con_estado_explicito_se_consultan_reparados_e_historicos(client, datos):
    reparado = datos("bache", "reparado").folio
    historico = datos("encharcamiento", "historico").folio
    datos("bache")
    assert folios(consultar(client, estado="reparado")) == [reparado]
    assert folios(consultar(client, estado="historico")) == [historico]


# --- HU-04.1 CA4: rechazados ------------------------------------------------------------------------
def test_el_publico_nunca_ve_rechazados(client, datos, ciudadano):
    datos("bache", "rechazado")
    datos("encharcamiento", "rechazado")
    assert folios(consultar(client, estado="rechazado")) == []
    assert folios(consultar(client, estado="rechazado", headers=encabezado_de(ciudadano))) == []


@pytest.mark.parametrize("rol", ["moderador", "coordinador"])
def test_moderacion_ve_rechazados_solo_si_los_pide(client, datos, crear_usuario, rol):
    usuario = crear_usuario(f"{rol}@ejemplo.test", rol=rol)
    rechazados = {datos("bache", "rechazado").folio, datos("encharcamiento", "rechazado").folio}
    abierto = datos("bache").folio
    token = encabezado_de(usuario)
    assert set(folios(consultar(client, estado="rechazado", headers=token))) == rechazados
    assert folios(consultar(client, headers=token)) == [abierto]  # por omisión, solo activos


def test_token_invalido_o_vencido_se_trata_como_publico(client, datos, moderador):
    datos("bache", "rechazado")
    vencido = encabezado_de(moderador, expira_en=timedelta(seconds=-1))
    for headers in (vencido, {"Authorization": "Bearer no-es-un-token"}):
        r = consultar(client, estado="rechazado", headers=headers)
        assert r.status_code == 200 and r.json()["total"] == 0


def test_moderador_suspendido_se_trata_como_publico(client, db, datos, moderador):
    datos("bache", "rechazado")
    moderador.activo = False
    db.commit()
    assert folios(consultar(client, estado="rechazado", headers=encabezado_de(moderador))) == []


# --- HU-04.2: filtros combinados, búsqueda y paginación ---------------------------------------------
def test_filtros_combinados(client, datos):
    objetivo = datos("bache", "validado", severidad="alta", colonia=datos.lejana).folio
    datos("bache", "validado", severidad="baja", colonia=datos.lejana)  # otra severidad
    datos("bache", "validado", severidad="alta")  # otra colonia
    datos("bache", "recibido", severidad="alta", colonia=datos.lejana)  # otro estado
    datos("encharcamiento", colonia=datos.lejana)  # otra categoría
    r = consultar(client, categoria="bache", estado="validado", severidad="alta", colonia_id=datos.lejana.id)
    assert folios(r) == [objetivo]
    assert folios(consultar(client, categoria="encharcamiento", colonia_id=datos.lejana.id)) != []


def test_busqueda_por_calle_o_folio_sin_distinguir_mayusculas(client, datos):
    tecnologico = datos("bache", calle="Av. Tecnológico").folio
    otro = datos("encharcamiento", calle="Calle Ejército Nacional").folio
    datos("bache", calle="Calle 100 Norte")
    assert folios(consultar(client, q="TECNOL")) == [tecnologico]
    assert folios(consultar(client, q=otro.lower())) == [otro]
    assert folios(consultar(client, q="  000002 ")) == [otro]  # parte del folio y con espacios
    assert folios(consultar(client, q="100%")) == []  # el % no funciona como comodín


def test_fechas_en_hora_de_juarez(client, datos):
    # 2026-11-21 05:30 UTC es el 20 de noviembre a las 23:30 en Juárez (UTC-7)
    noche = datos("bache", creado_en=datetime(2026, 11, 21, 5, 30, tzinfo=UTC)).folio
    manana = datos("bache", creado_en=datetime(2026, 11, 21, 15, 0, tzinfo=UTC)).folio
    assert folios(consultar(client, desde="2026-11-20", hasta="2026-11-20")) == [noche]
    assert folios(consultar(client, desde="2026-11-21")) == [manana]
    assert folios(consultar(client, hasta="2026-11-21")) == [manana, noche]


def test_pagina_de_20_con_el_total(client, datos):
    creados = [datos("bache").folio for _ in range(25)]
    primera = consultar(client)
    assert len(primera.json()["items"]) == 20 and primera.json()["total"] == 25
    segunda = consultar(client, pagina=2)
    assert folios(segunda) == list(reversed(creados))[20:]
    assert segunda.json()["pagina"] == 2 and segunda.json()["total"] == 25
    assert folios(consultar(client, pagina=3)) == []
    assert len(consultar(client, tam=5).json()["items"]) == 5


@pytest.mark.parametrize(
    ("params", "campo"),
    [
        ({"desde": "2026-13-01"}, "desde"),
        ({"hasta": "ayer"}, "hasta"),
        ({"desde": "2026-11-21", "hasta": "2026-11-20"}, "hasta"),
        ({"categoria": "grafiti"}, "categoria"),
        ({"estado": "abierto"}, "estado"),
        ({"severidad": "extrema"}, "severidad"),
        ({"pagina": 0}, "pagina"),
        ({"tam": 1000}, "tam"),
        ({"colonia_id": "uno"}, "colonia_id"),
        ({"q": "x" * 101}, "q"),
    ],
)
def test_parametros_invalidos_responden_422_por_campo(client, params, campo):
    r = consultar(client, **params)
    assert r.status_code == 422
    assert r.json()["codigo"] == "VALIDACION" and campo in r.json()["campos"]


# --- Vigencia de encharcamientos --------------------------------------------------------------------
def test_vence_encharcamientos_antes_de_consultar(client, db, datos):
    vencido = datos("encharcamiento", vigente_hasta=ahora_utc() - timedelta(minutes=1))
    vigente = datos("encharcamiento").folio
    assert folios(consultar(client)) == [vigente]
    db.refresh(vencido)
    assert vencido.estado == "historico"
    assert folios(consultar(client, estado="historico")) == [vencido.folio]


# --- La función de filtrado se puede reutilizar (tablero, HU-07.1 CA5) ------------------------------
def test_funcion_de_filtrado_con_sector_y_sin_rechazados(db, datos):
    lejano = datos("bache", "validado", colonia=datos.lejana)
    datos("bache", "validado")
    datos("bache", "rechazado", colonia=datos.lejana)

    filtro = FiltroReportes(sector_id=datos.sector_lejano.id, estados=("validado", "rechazado"))
    assert [r.id for r in db.scalars(consulta_reportes(filtro))] == [lejano.id]

    con_rechazados = FiltroReportes(sector_id=datos.sector_lejano.id, estados=("validado", "rechazado"),
                                    incluir_rechazados=True)
    assert len(list(db.scalars(consulta_reportes(con_rechazados)))) == 2
    # Sin filtros: solo activos y en orden (más reciente primero)
    assert [r.estado for r in db.scalars(consulta_reportes(FiltroReportes()))] == ["validado", "validado"]
