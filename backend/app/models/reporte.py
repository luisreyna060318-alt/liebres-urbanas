"""Reportes (baches y encharcamientos en una sola tabla), confirmaciones, historial, avisos y folios."""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    event,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.reglas import (
    CARRILES,
    CATEGORIAS,
    COMENTARIO_MAX,
    DESCRIPCION_MAX,
    ESTADOS_BACHE,
    ESTADOS_ENCHARCAMIENTO,
    NIVELES_AGUA,
    PREFIJOS_FOLIO,
    PROFUNDIDADES,
    SEVERIDADES,
    TAMANOS,
    TIPOS_CONFIRMACION,
    valores_sql,
)
from app.core.tiempo import FechaHoraUTC, ahora_utc

# Un reporte trae solo los campos de su categoría; los de la otra quedan en NULL (DISENO_TECNICO, sección 3).
# Las reglas finas por tipo de daño (p. ej. "bache" exige tamaño, profundidad y carril) las valida el servicio,
# porque dependen de otra tabla y un CHECK no puede consultarla.
CHECK_BACHE = (
    "categoria = 'bache'"
    " AND tipo_dano_id IS NOT NULL AND severidad IS NOT NULL"
    " AND nivel_agua IS NULL AND hay_riesgo IS NULL AND vigente_hasta IS NULL"
    f" AND estado IN {valores_sql(ESTADOS_BACHE)}"
    # la fecha de reparación existe si y solo si el bache está reparado
    " AND ((estado = 'reparado' AND fecha_reparacion IS NOT NULL)"
    " OR (estado <> 'reparado' AND fecha_reparacion IS NULL))"
)
CHECK_ENCHARCAMIENTO = (
    "categoria = 'encharcamiento'"
    " AND tipo_dano_id IS NULL AND severidad IS NULL AND tamano IS NULL AND profundidad IS NULL"
    " AND carril IS NULL AND senalizado IS NULL AND fecha_reparacion IS NULL"
    " AND nivel_agua IS NOT NULL AND vigente_hasta IS NOT NULL"
    f" AND estado IN {valores_sql(ESTADOS_ENCHARCAMIENTO)}"
    # "intransitable" exige responder si hay vehículos varados o personas en riesgo (HU-03.1 CA3)
    " AND (nivel_agua <> 'intransitable' OR hay_riesgo IS NOT NULL)"
)


class Reporte(Base):
    """Un bache o un encharcamiento. `creado_en` lo asigna el servidor y no cambia nunca (RN-10)."""

    __tablename__ = "reportes"

    id: Mapped[int] = mapped_column(primary_key=True)
    folio: Mapped[str] = mapped_column(String(20), unique=True)  # BCH-2026-000123 / ENC-2026-000045
    categoria: Mapped[str] = mapped_column(String(20))
    tipo_dano_id: Mapped[int | None] = mapped_column(ForeignKey("tipos_dano.id"))  # solo baches
    autor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    colonia_id: Mapped[int] = mapped_column(ForeignKey("colonias.id"))
    calle: Mapped[str] = mapped_column(String(150))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    descripcion: Mapped[str | None] = mapped_column(String(DESCRIPCION_MAX))

    # --- Solo baches ---
    severidad: Mapped[str | None] = mapped_column(String(10))  # la calcula el servidor
    tamano: Mapped[str | None] = mapped_column(String(10))
    profundidad: Mapped[str | None] = mapped_column(String(10))
    carril: Mapped[str | None] = mapped_column(String(10))
    senalizado: Mapped[bool | None] = mapped_column(Boolean)  # alcantarilla sin tapa
    fecha_reparacion: Mapped[date | None] = mapped_column(Date)

    # --- Solo encharcamientos ---
    nivel_agua: Mapped[str | None] = mapped_column(String(20))
    hay_riesgo: Mapped[bool | None] = mapped_column(Boolean)
    vigente_hasta: Mapped[datetime | None] = mapped_column(FechaHoraUTC)

    # --- Seguimiento ---
    estado: Mapped[str] = mapped_column(String(20))
    confirmaciones: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    creado_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc, server_default=func.now())
    motivo_rechazo_id: Mapped[int | None] = mapped_column(ForeignKey("motivos_rechazo.id"))
    motivo_texto: Mapped[str | None] = mapped_column(String(DESCRIPCION_MAX))

    tipo_dano = relationship("TipoDano")
    colonia = relationship("Colonia")
    motivo_rechazo = relationship("MotivoRechazo")
    # passive_deletes="all": el ORM nunca borra filas del historial; si se borra un reporte en "recibido"
    # (HU-02.5), lo hace la base con ON DELETE CASCADE (el trigger de PostgreSQL lo permite solo en ese caso).
    historial: Mapped[list["HistorialEstado"]] = relationship(
        back_populates="reporte", passive_deletes="all", order_by="HistorialEstado.id"
    )

    __table_args__ = (
        CheckConstraint(f"categoria IN {valores_sql(CATEGORIAS)}", name="categoria_valida"),
        CheckConstraint(f"({CHECK_BACHE}) OR ({CHECK_ENCHARCAMIENTO})", name="campos_por_categoria"),
        CheckConstraint(f"descripcion IS NULL OR length(descripcion) <= {DESCRIPCION_MAX}", name="descripcion_max"),
        CheckConstraint(f"severidad IS NULL OR severidad IN {valores_sql(SEVERIDADES)}", name="severidad_valida"),
        CheckConstraint(f"tamano IS NULL OR tamano IN {valores_sql(TAMANOS)}", name="tamano_valido"),
        CheckConstraint(
            f"profundidad IS NULL OR profundidad IN {valores_sql(PROFUNDIDADES)}", name="profundidad_valida"
        ),
        CheckConstraint(f"carril IS NULL OR carril IN {valores_sql(CARRILES)}", name="carril_valido"),
        CheckConstraint(f"nivel_agua IS NULL OR nivel_agua IN {valores_sql(NIVELES_AGUA)}", name="nivel_agua_valido"),
        CheckConstraint("confirmaciones >= 0", name="confirmaciones_no_negativas"),
        # Índices para que la consulta pública responda rápido con 500+ reportes (RNF-06)
        Index("ix_reportes_categoria_estado", "categoria", "estado"),
        Index("ix_reportes_colonia_id", "colonia_id"),
        Index("ix_reportes_creado_en", "creado_en"),
        Index("ix_reportes_lat_lon", "lat", "lon"),
    )


class Confirmacion(Base):
    """Respuesta de una persona sobre un reporte (relación N:M con datos propios: tipo y fecha)."""

    __tablename__ = "confirmaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    reporte_id: Mapped[int] = mapped_column(ForeignKey("reportes.id", ondelete="CASCADE"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    tipo: Mapped[str] = mapped_column(String(20))
    creado_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc, server_default=func.now())

    __table_args__ = (
        # Una persona responde una sola vez por reporte (HU-02.3 CA3, HU-03.3 CA2)
        UniqueConstraint("reporte_id", "usuario_id"),
        CheckConstraint(f"tipo IN {valores_sql(TIPOS_CONFIRMACION)}", name="tipo_valido"),
    )


class HistorialEstado(Base):
    """Cada cambio de estado de un reporte. Solo se inserta: nunca se modifica ni se borra (RN-07).

    Protecciones: (1) ninguna ruta lo edita, (2) los eventos de SQLAlchemy de abajo lanzan error,
    (3) un trigger en PostgreSQL rechaza UPDATE y DELETE (migración 0001).
    actor_id NULL significa "sistema" (por ejemplo, un encharcamiento que vence solo, HU-03.2).
    """

    __tablename__ = "historial_estados"

    id: Mapped[int] = mapped_column(primary_key=True)
    reporte_id: Mapped[int] = mapped_column(ForeignKey("reportes.id", ondelete="CASCADE"), index=True)
    estado_anterior: Mapped[str | None] = mapped_column(String(20))  # NULL en el alta del reporte
    estado_nuevo: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    comentario: Mapped[str | None] = mapped_column(String(COMENTARIO_MAX))  # público
    creado_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc, server_default=func.now())

    reporte: Mapped[Reporte] = relationship(back_populates="historial")
    actor = relationship("Usuario")


class HistorialInalterable(Exception):
    """Se intentó modificar o borrar una fila del historial de estados."""


@event.listens_for(HistorialEstado, "before_update")
def _impedir_actualizar_historial(_mapper, _conexion, fila: HistorialEstado) -> None:
    raise HistorialInalterable(f"El historial de estados no se puede modificar (fila {fila.id})")


@event.listens_for(HistorialEstado, "before_delete")
def _impedir_borrar_historial(_mapper, _conexion, fila: HistorialEstado) -> None:
    raise HistorialInalterable(f"El historial de estados no se puede borrar (fila {fila.id})")


class Notificacion(Base):
    """Aviso para el autor cuando cambia el estado de su reporte (HU-08.2, P1)."""

    __tablename__ = "notificaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    reporte_id: Mapped[int] = mapped_column(ForeignKey("reportes.id", ondelete="CASCADE"))
    mensaje: Mapped[str] = mapped_column(String(300))
    leida: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    creado_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc, server_default=func.now())


class FolioContador(Base):
    """Último consecutivo usado por prefijo y año. Se lee con bloqueo de fila al crear un folio (RN-03)."""

    __tablename__ = "folio_contadores"

    prefijo: Mapped[str] = mapped_column(String(3), primary_key=True)
    anio: Mapped[int] = mapped_column(Integer, primary_key=True)
    ultimo: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    __table_args__ = (
        CheckConstraint(f"prefijo IN {valores_sql(tuple(PREFIJOS_FOLIO.values()))}", name="prefijo_valido"),
        CheckConstraint("ultimo >= 0", name="ultimo_no_negativo"),
    )
