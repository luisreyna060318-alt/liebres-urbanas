"""Esquemas de reportes (CONTRATO_API, sección 6) y los serializadores que los arman.

PRIVACIDAD (RN-04): ningún esquema de SALIDA de este archivo tiene autor_id, nombre ni correo del autor. Si se
agrega un campo, revisa que no identifique a la persona: las pruebas de privacidad recorren el JSON buscando
llaves prohibidas.

Cómo usarlos desde otro router (por ejemplo, la consulta pública de Carlos):

    from app.core.tiempo import hoy_local
    from app.schemas.reportes import ReportePublico, a_reporte_publico
    from app.services.encharcamientos import expirar_vencidos   # (rama L10) llámalo ANTES de leer

    @router.get("/reportes", response_model=Pagina[ReportePublico])
    def consultar(db: SesionDB, ...):
        expirar_vencidos(db)                       # pasa a "historico" los encharcamientos vencidos
        pagina = paginar(db, consulta, pagina, tam)
        hoy = hoy_local()                          # una sola vez por petición
        pagina["items"] = [a_reporte_publico(r, hoy) for r in pagina["items"]]
        return pagina

Los serializadores leen las relaciones tipo_dano, colonia y motivo_rechazo; para listas largas conviene
cargar esas relaciones con joinedload en la consulta.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.reglas import (
    CARRILES,
    CATEGORIAS,
    DESCRIPCION_MAX,
    NIVELES_AGUA,
    PROFUNDIDADES,
    SEVERIDADES,
    TAMANOS,
    TIPOS_CONFIRMACION,
)
from app.core.tiempo import a_hora_local
from app.models import Reporte

CALLE_MAX = 150

# Estados en los que un bache sigue "abierto" (se busca duplicado y se puede confirmar)
ESTADOS_BACHE_ABIERTOS = ("recibido", "validado", "en_reparacion")


# =====================================================================================================
# Entrada
# =====================================================================================================
class _UbicacionEntrada(BaseModel):
    """Campos de ubicación comunes a baches y encharcamientos. `creado_en` NO existe aquí: lo pone el servidor."""

    lat: float = Field(ge=-90, le=90, examples=[31.7001])
    lon: float = Field(ge=-180, le=180, examples=[-106.4302])
    calle: str = Field(examples=["Av. Tecnológico"], description=f"Hasta {CALLE_MAX} caracteres")
    colonia_id: int = Field(examples=[12], description="Colonia activa del catálogo (GET /api/colonias)")
    descripcion: str | None = Field(
        default=None, examples=["Hueco grande junto al semáforo"], description=f"Opcional, hasta {DESCRIPCION_MAX}"
    )

    @field_validator("calle")
    @classmethod
    def validar_calle(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("Escribe la calle")
        if len(v) > CALLE_MAX:
            raise ValueError(f"La calle no puede pasar de {CALLE_MAX} caracteres")
        return v

    @field_validator("descripcion")
    @classmethod
    def validar_descripcion(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if len(v) > DESCRIPCION_MAX:
            raise ValueError(f"La descripción no puede pasar de {DESCRIPCION_MAX} caracteres")
        return v or None  # "" se guarda como "sin descripción"


class BacheEdicion(_UbicacionEntrada):
    """Campos editables de un bache (PUT /api/reportes/{id}). Qué campos exige cada tipo de daño lo valida el
    servicio (services/reportes.py), porque depende del tipo elegido."""

    tipo_dano_codigo: str = Field(examples=["bache"], description="bache, hundimiento, grieta o alcantarilla_sin_tapa")
    tamano: Literal[TAMANOS] | None = Field(default=None, examples=["grande"])
    profundidad: Literal[PROFUNDIDADES] | None = Field(default=None, examples=["media"])
    carril: Literal[CARRILES] | None = Field(default=None, examples=["derecho"])
    senalizado: bool | None = Field(default=None, description="Solo alcantarilla sin tapa: ¿está señalizada?")


class BacheEntrada(BacheEdicion):
    """Alta de un bache (POST /api/reportes/baches)."""

    forzar: bool = Field(default=False, description="true = crear aunque haya un bache abierto a 30 m o menos")


class ConfirmacionEntrada(BaseModel):
    """POST /api/reportes/{id}/confirmaciones: `confirma` (bache), `sigue` o `ya_no_hay` (encharcamiento)."""

    tipo: Literal[TIPOS_CONFIRMACION] = Field(examples=["confirma"])


# =====================================================================================================
# Salida (NUNCA con datos del autor)
# =====================================================================================================
class TipoDanoCorto(BaseModel):
    codigo: str = Field(examples=["bache"])
    nombre: str = Field(examples=["Bache"])


class ColoniaCorta(BaseModel):
    id: int = Field(examples=[12])
    nombre: str = Field(examples=["Partido Escobedo"])


class ReportePublico(BaseModel):
    """Lo que ve cualquier persona (CONTRATO_API 6.1). Los campos de la otra categoría vienen en null."""

    id: int
    folio: str = Field(examples=["BCH-2026-000123"])
    categoria: Literal[CATEGORIAS]
    tipo_dano: TipoDanoCorto | None = Field(description="null en encharcamientos")
    calle: str
    colonia: ColoniaCorta
    lat: float
    lon: float
    descripcion: str | None
    severidad: Literal[SEVERIDADES] | None
    tamano: str | None
    profundidad: str | None
    carril: str | None
    senalizado: bool | None
    nivel_agua: Literal[NIVELES_AGUA] | None
    hay_riesgo: bool | None
    estado: str = Field(examples=["recibido"])
    sin_validar: bool = Field(description="true solo para baches en «recibido» (RN-09)")
    confirmaciones: int
    creado_en: datetime
    vigente_hasta: datetime | None
    fecha_reparacion: date | None
    antiguedad_dias: int = Field(description="Días desde creado_en hasta hoy, o hasta fecha_reparacion (RN-10)")


class MotivoRechazoMio(BaseModel):
    nombre: str = Field(examples=["Duplicado"])
    texto: str | None = Field(description="Explicación del moderador, si la escribió")


class ReporteMio(ReportePublico):
    """ReportePublico + datos que solo ve el autor."""

    puede_editar: bool = Field(description="true únicamente en «recibido»")
    motivo_rechazo: MotivoRechazoMio | None


class Cercano(ReportePublico):
    """Reporte cercano a un punto (duplicados, HU-02.3) con su distancia en metros."""

    distancia_m: int = Field(examples=[12])


class CambioEstado(BaseModel):
    """Una fila del historial público. NO incluye quién hizo el cambio."""

    estado_anterior: str | None
    estado_nuevo: str
    comentario: str | None
    creado_en: datetime


class ReporteDetalle(ReportePublico):
    """Detalle de un reporte (GET /api/reportes/{id}, lo construye Carlos)."""

    longevidad_dias: int
    ultima_actividad: datetime
    historial: list[CambioEstado] = Field(description="Del más reciente al más antiguo")


# =====================================================================================================
# Serializadores: modelo Reporte -> esquema de salida
# =====================================================================================================
def antiguedad_dias(reporte: Reporte, hoy: date) -> int:
    """RN-10: días desde que se creó (fecha de Juárez) hasta hoy, o hasta la reparación si ya se reparó."""
    fin = reporte.fecha_reparacion if reporte.estado == "reparado" and reporte.fecha_reparacion else hoy
    return max((fin - a_hora_local(reporte.creado_en).date()).days, 0)


def _campos_publicos(reporte: Reporte, hoy: date) -> dict:
    """Diccionario con los campos de ReportePublico. Se escribe campo por campo a propósito: así nunca se cuela
    autor_id ni otro dato privado aunque el modelo crezca."""
    return {
        "id": reporte.id,
        "folio": reporte.folio,
        "categoria": reporte.categoria,
        "tipo_dano": (
            {"codigo": reporte.tipo_dano.codigo, "nombre": reporte.tipo_dano.nombre} if reporte.tipo_dano else None
        ),
        "calle": reporte.calle,
        "colonia": {"id": reporte.colonia.id, "nombre": reporte.colonia.nombre},
        "lat": reporte.lat,
        "lon": reporte.lon,
        "descripcion": reporte.descripcion,
        "severidad": reporte.severidad,
        "tamano": reporte.tamano,
        "profundidad": reporte.profundidad,
        "carril": reporte.carril,
        "senalizado": reporte.senalizado,
        "nivel_agua": reporte.nivel_agua,
        "hay_riesgo": reporte.hay_riesgo,
        "estado": reporte.estado,
        "sin_validar": reporte.categoria == "bache" and reporte.estado == "recibido",
        "confirmaciones": reporte.confirmaciones,
        "creado_en": reporte.creado_en,
        "vigente_hasta": reporte.vigente_hasta,
        "fecha_reparacion": reporte.fecha_reparacion,
        "antiguedad_dias": antiguedad_dias(reporte, hoy),
    }


def a_reporte_publico(reporte: Reporte, hoy: date) -> ReportePublico:
    """Reporte -> ReportePublico. `hoy` es hoy_local() (se pasa para calcularlo una vez por petición)."""
    return ReportePublico(**_campos_publicos(reporte, hoy))


def a_reporte_mio(reporte: Reporte, hoy: date) -> ReporteMio:
    """Reporte -> ReporteMio (solo para su autor)."""
    motivo = None
    if reporte.estado == "rechazado" and reporte.motivo_rechazo is not None:
        motivo = {"nombre": reporte.motivo_rechazo.nombre, "texto": reporte.motivo_texto}
    return ReporteMio(
        **_campos_publicos(reporte, hoy), puede_editar=reporte.estado == "recibido", motivo_rechazo=motivo
    )


def a_cercano(reporte: Reporte, hoy: date, distancia: float) -> Cercano:
    """Reporte -> Cercano, con la distancia redondeada a metros enteros."""
    return Cercano(**_campos_publicos(reporte, hoy), distancia_m=round(distancia))


def a_reporte_detalle(reporte: Reporte, hoy: date) -> ReporteDetalle:
    """Reporte -> ReporteDetalle. El historial sale del más reciente al más antiguo y SIN el actor."""
    filas = sorted(reporte.historial, key=lambda f: f.id, reverse=True)
    historial = [
        CambioEstado(
            estado_anterior=f.estado_anterior, estado_nuevo=f.estado_nuevo, comentario=f.comentario,
            creado_en=f.creado_en,
        )
        for f in filas
    ]
    ultima = filas[0].creado_en if filas else reporte.creado_en
    publico = _campos_publicos(reporte, hoy)
    return ReporteDetalle(
        **publico, longevidad_dias=publico["antiguedad_dias"], ultima_actividad=ultima, historial=historial
    )
