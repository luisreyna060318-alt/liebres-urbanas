"""Alta de baches: HU-02.1 (reportar un bache) y HU-02.2 (describir el daño según su tipo)."""

from datetime import timedelta

import pytest
from sqlalchemy import event, select
from sqlalchemy.dialects import postgresql

from app.core.reglas import DESCRIPCION_MAX, MAX_REPORTES_POR_HORA
from app.core.tiempo import ahora_utc, como_utc
from app.models import FolioContador, HistorialEstado, Reporte, Usuario
from app.schemas.reportes import BacheEntrada
from app.services import reportes as reportes_service
from app.services.reportes import calcular_severidad
from app.services.validaciones import validar_limite_horario
from tests.conftest import LLAVES_PROHIBIDAS, datos_bache, encabezado_de, llaves_de

RUTA = "/api/reportes/baches"


@pytest.fixture()
def alta(client, ciudadano, catalogo):
    """alta(n=0, **cambios) -> respuesta de POST /api/reportes/baches como el ciudadano de prueba."""

    def _alta(n: int = 0, usuario=None, **cambios):
        return client.post(
            RUTA, json=datos_bache(catalogo["colonia"].id, n, **cambios), headers=encabezado_de(usuario or ciudadano)
        )

    return _alta


# --- HU-02.1 -------------------------------------------------------------------------------------
def test_ca3_crea_bache_con_folio_fecha_del_servidor_y_estado_recibido(alta, db, catalogo):
    antes = ahora_utc()
    r = alta()
    assert r.status_code == 201
    datos = r.json()
    assert datos["folio"].startswith("BCH-") and len(datos["folio"]) == len("BCH-2026-000001")
    assert datos["estado"] == "recibido" and datos["sin_validar"] is True
    assert datos["categoria"] == "bache" and datos["confirmaciones"] == 0
    assert datos["tipo_dano"] == {"codigo": "bache", "nombre": "Bache"}
    assert datos["colonia"] == {"id": catalogo["colonia"].id, "nombre": "Partido Escobedo"}
    assert datos["puede_editar"] is True and datos["motivo_rechazo"] is None
    assert datos["antiguedad_dias"] == 0
    assert datos["nivel_agua"] is None and datos["vigente_hasta"] is None
    creado = como_utc(db.get(Reporte, datos["id"]).creado_en)
    assert antes - timedelta(seconds=1) <= creado <= ahora_utc() + timedelta(seconds=1)
    assert datos["creado_en"].endswith("Z")


def test_ca3_deja_la_primera_fila_del_historial(alta, db, ciudadano):
    reporte_id = alta().json()["id"]
    filas = list(db.scalars(select(HistorialEstado).where(HistorialEstado.reporte_id == reporte_id)))
    assert len(filas) == 1
    assert filas[0].estado_anterior is None and filas[0].estado_nuevo == "recibido"
    assert filas[0].actor_id == ciudadano.id


def test_ca3_ignora_un_creado_en_enviado(alta, db):
    r = alta(creado_en="2020-01-01T00:00:00Z", estado="reparado", severidad="baja", confirmaciones=50)
    assert r.status_code == 201
    datos = r.json()
    assert not datos["creado_en"].startswith("2020")
    assert datos["estado"] == "recibido" and datos["confirmaciones"] == 0
    assert datos["severidad"] == "media"  # la calcula el servidor, no la persona


def test_folios_consecutivos(alta):
    folios = [alta(n).json()["folio"] for n in range(3)]
    numeros = [int(f.rsplit("-", 1)[1]) for f in folios]
    assert numeros == [numeros[0], numeros[0] + 1, numeros[0] + 2]
    assert len({f.split("-")[1] for f in folios}) == 1  # mismo año


@pytest.mark.parametrize(
    "lat,lon", [(28.6353, -106.0889), (19.4326, -99.1332), (31.9000, -106.4000)]
)
def test_ca2_fuera_del_municipio_responde_422(alta, db, lat, lon):
    r = alta(lat=lat, lon=lon)
    assert r.status_code == 422
    assert r.json()["codigo"] == "FUERA_DEL_MUNICIPIO"
    assert db.scalar(select(Reporte)) is None


def test_ca1_calle_y_colonia_corregibles(alta, catalogo):
    datos = alta(calle="  Calle   Corregida  ").json()
    assert datos["calle"] == "Calle Corregida"


def test_colonia_inexistente_o_desactivada(alta, catalogo):
    for colonia_id in (catalogo["inactiva"].id, 9999):
        r = alta(colonia_id=colonia_id)
        assert r.status_code == 422 and "colonia_id" in r.json()["campos"]


def test_campos_obligatorios_con_mensajes_en_espanol(client, ciudadano, catalogo):
    r = client.post(RUTA, json={"tipo_dano_codigo": "bache"}, headers=encabezado_de(ciudadano))
    assert r.status_code == 422
    campos = r.json()["campos"]
    for campo in ("lat", "lon", "calle", "colonia_id"):
        assert campos[campo] == "Este campo es obligatorio"


def test_valores_no_permitidos(alta):
    r = alta(tamano="enorme", carril="centro")
    assert r.status_code == 422
    assert set(r.json()["campos"]) >= {"tamano", "carril"}


def test_tipo_de_dano_desconocido(alta):
    r = alta(tipo_dano_codigo="volcan")
    assert r.status_code == 422 and "tipo_dano_codigo" in r.json()["campos"]


def test_tipo_de_dano_desactivado(alta, db, catalogo):
    catalogo["tipos"]["grieta"].activo = False
    db.commit()
    assert alta(tipo_dano_codigo="grieta").status_code == 422


# --- HU-02.2: campos por tipo de daño --------------------------------------------------------------
def test_bache_exige_tamano_profundidad_y_carril(alta):
    r = alta(tamano=None, profundidad=None, carril=None)
    assert r.status_code == 422
    assert set(r.json()["campos"]) == {"tamano", "profundidad", "carril"}


@pytest.mark.parametrize("tipo", ["hundimiento", "grieta"])
def test_hundimiento_y_grieta_exigen_tamano_y_carril(alta, tipo):
    r = alta(tipo_dano_codigo=tipo, tamano=None, profundidad=None, carril=None)
    assert r.status_code == 422
    assert set(r.json()["campos"]) == {"tamano", "carril"}
    ok = alta(tipo_dano_codigo=tipo, tamano="chico", profundidad=None, carril="orilla")
    assert ok.status_code == 201
    assert ok.json()["tipo_dano"]["codigo"] == tipo and ok.json()["severidad"] == "baja"


def test_alcantarilla_exige_senalizado_y_es_alta(alta):
    r = alta(tipo_dano_codigo="alcantarilla_sin_tapa", senalizado=None, tamano=None, profundidad=None, carril=None)
    assert r.status_code == 422 and set(r.json()["campos"]) == {"senalizado"}
    ok = alta(tipo_dano_codigo="alcantarilla_sin_tapa", senalizado=False, tamano="chico", profundidad="baja")
    assert ok.status_code == 201
    assert ok.json()["severidad"] == "alta" and ok.json()["senalizado"] is False


def test_senalizado_solo_se_guarda_en_alcantarillas(alta):
    assert alta(senalizado=True).json()["senalizado"] is None


@pytest.mark.parametrize(
    "tipo,tamano,profundidad,esperada",
    [
        ("alcantarilla_sin_tapa", None, None, "alta"),
        ("alcantarilla_sin_tapa", "chico", "baja", "alta"),
        ("bache", "grande", "baja", "alta"),
        ("bache", "chico", "alta", "alta"),
        ("bache", "mediano", "media", "media"),
        ("grieta", "mediano", None, "media"),
        ("bache", "chico", "media", "baja"),
        ("hundimiento", "chico", None, "baja"),
    ],
)
def test_calcular_severidad(tipo, tamano, profundidad, esperada):
    assert calcular_severidad(tipo, tamano, profundidad) == esperada


def test_ca4_descripcion_maxima_validada_en_el_servidor(alta):
    assert alta(descripcion="x" * DESCRIPCION_MAX).status_code == 201
    r = alta(n=1, descripcion="x" * (DESCRIPCION_MAX + 1))
    assert r.status_code == 422 and "descripcion" in r.json()["campos"]


def test_descripcion_vacia_queda_en_null(alta):
    assert alta(descripcion="   ").json()["descripcion"] is None


# --- Roles, sesión y privacidad ------------------------------------------------------------------
def test_sin_token_responde_401(client, catalogo):
    r = client.post(RUTA, json=datos_bache(catalogo["colonia"].id))
    assert r.status_code == 401 and r.json()["codigo"] == "NO_AUTENTICADO"


@pytest.mark.parametrize("rol", ["moderador", "coordinador"])
def test_moderador_y_coordinador_no_crean_reportes(alta, crear_usuario, rol):
    r = alta(usuario=crear_usuario(f"{rol}@ejemplo.test", rol=rol))
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"


def test_cuenta_suspendida_no_crea(alta, crear_usuario):
    suspendida = crear_usuario("suspendida@ejemplo.test", activo=False)
    assert alta(usuario=suspendida).json()["codigo"] == "CUENTA_SUSPENDIDA"


def test_la_respuesta_no_contiene_datos_del_autor(alta, ciudadano):
    r = alta()
    assert not (llaves_de(r.json()) & LLAVES_PROHIBIDAS)
    assert ciudadano.correo not in r.text and ciudadano.nombre not in r.text


# --- Límite por hora ------------------------------------------------------------------------------
def test_el_reporte_11_en_una_hora_responde_429(alta, db):
    for n in range(MAX_REPORTES_POR_HORA):
        assert alta(n).status_code == 201
    r = alta(MAX_REPORTES_POR_HORA)
    assert r.status_code == 429 and r.json()["codigo"] == "LIMITE_HORARIO"
    assert len(list(db.scalars(select(Reporte)))) == MAX_REPORTES_POR_HORA


def test_el_limite_es_por_cuenta(alta, crear_usuario):
    for n in range(MAX_REPORTES_POR_HORA):
        alta(n)
    otra = crear_usuario("otra@ejemplo.test")
    assert alta(50, usuario=otra).status_code == 201


def test_pasada_una_hora_se_puede_volver_a_reportar(db, ciudadano, catalogo):
    """Se inyecta la hora en el servicio (sin dormir): 10 reportes hace 61 minutos ya no cuentan."""
    hace_61_min = ahora_utc() - timedelta(minutes=61)
    for n in range(MAX_REPORTES_POR_HORA):
        reportes_service.crear_bache(db, ciudadano, BacheEntrada(**datos_bache(catalogo["colonia"].id, n)), hace_61_min)
    nuevo = reportes_service.crear_bache(db, ciudadano, BacheEntrada(**datos_bache(catalogo["colonia"].id, 20)))
    assert nuevo.estado == "recibido"


def _bloqueos_pedidos(db, accion) -> list[str]:
    """Ejecuta `accion` y devuelve, en orden, las tablas que se leyeron con SELECT ... FOR UPDATE.

    SQLite no ejerce el bloqueo de fila (ni siquiera escribe FOR UPDATE), así que cada consulta del ORM se
    traduce al SQL de PostgreSQL para comprobar que el bloqueo SÍ se pide en la base real.
    """
    tablas = []

    def _al_ejecutar(estado):
        if estado.is_select and estado.bind_mapper is not None:
            sql = str(estado.statement.compile(dialect=postgresql.dialect()))
            if "FOR UPDATE" in sql:
                tablas.append(estado.bind_mapper.local_table.name)

    event.listen(db, "do_orm_execute", _al_ejecutar)
    try:
        accion()
    finally:
        event.remove(db, "do_orm_execute", _al_ejecutar)
    return tablas


def test_el_limite_bloquea_la_fila_de_la_persona(db, ciudadano):
    """S1: el conteo del límite se hace con la fila del usuario bloqueada, así las altas simultáneas de una
    misma cuenta se forman en fila y la ráfaga ya no se salta el límite."""
    tablas = _bloqueos_pedidos(db, lambda: validar_limite_horario(db, ciudadano, ahora_utc()))
    assert tablas == [Usuario.__tablename__]


def test_el_alta_bloquea_primero_al_usuario_y_despues_el_folio(db, ciudadano, catalogo):
    """Mismo orden de bloqueos en toda alta (usuario -> contador de folios): dos peticiones nunca se esperan
    una a la otra en círculo."""
    entrada = BacheEntrada(**datos_bache(catalogo["colonia"].id, 1))
    tablas = _bloqueos_pedidos(db, lambda: reportes_service.crear_bache(db, ciudadano, entrada))
    assert tablas[0] == Usuario.__tablename__
    assert FolioContador.__tablename__ in tablas
    assert tablas.count(Usuario.__tablename__) == 1  # la fila del usuario se bloquea una sola vez
