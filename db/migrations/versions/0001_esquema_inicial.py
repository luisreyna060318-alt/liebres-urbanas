"""Esquema inicial: las 11 tablas de DISENO_TECNICO (sección 3), sus restricciones e índices.

Además, SOLO en PostgreSQL, dos triggers:
  (a) reportes.creado_en no puede cambiar nunca (RN-10).
  (b) historial_estados solo admite INSERT: rechaza UPDATE y DELETE (RN-07, HU-05.2 CA4).
      Única excepción: el borrado en cascada cuando se elimina el reporte completo (un reporte en
      "recibido" que su autor borra, HU-02.5); un DELETE directo sobre el historial sigue rechazado.
SQLite (pruebas) no tiene esos triggers; ahí protegen los eventos del ORM (app/models/reporte.py).

Generada con --autogenerate y revisada a mano: los tipos son de SQLAlchemy (no del código de la app) y
los valores por omisión usan sa.func.now()/sa.true()/sa.false() para que funcione en PostgreSQL y SQLite.

Revision ID: 0001
Revises:
Create Date: 2026-11-24 23:40:28.814839
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- Triggers de PostgreSQL ---------------------------------------------------------------------
TRIGGER_CREADO_EN = """
CREATE FUNCTION reportes_creado_en_fijo() RETURNS trigger AS $$
BEGIN
    IF NEW.creado_en IS DISTINCT FROM OLD.creado_en THEN
        RAISE EXCEPTION 'La fecha de creación de un reporte no se puede cambiar (reporte %)', OLD.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER reportes_creado_en_fijo
    BEFORE UPDATE ON reportes
    FOR EACH ROW EXECUTE FUNCTION reportes_creado_en_fijo();
"""

TRIGGER_HISTORIAL = """
CREATE FUNCTION historial_solo_insercion() RETURNS trigger AS $$
BEGIN
    -- Borrado en cascada: el reporte ya no existe, así que se permite borrar su historial
    IF TG_OP = 'DELETE' AND NOT EXISTS (SELECT 1 FROM reportes WHERE id = OLD.reporte_id) THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION 'El historial de estados no se puede modificar ni borrar (fila %)', OLD.id;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER historial_solo_insercion
    BEFORE UPDATE OR DELETE ON historial_estados
    FOR EACH ROW EXECUTE FUNCTION historial_solo_insercion();
"""


def es_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.create_table('folio_contadores',
    sa.Column('prefijo', sa.String(length=3), nullable=False),
    sa.Column('anio', sa.Integer(), nullable=False),
    sa.Column('ultimo', sa.Integer(), server_default='0', nullable=False),
    sa.CheckConstraint("prefijo IN ('BCH', 'ENC')", name=op.f('ck_folio_contadores_prefijo_valido')),
    sa.CheckConstraint('ultimo >= 0', name=op.f('ck_folio_contadores_ultimo_no_negativo')),
    sa.PrimaryKeyConstraint('prefijo', 'anio', name=op.f('pk_folio_contadores'))
    )
    op.create_table('motivos_rechazo',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(length=40), nullable=False),
    sa.Column('nombre', sa.String(length=80), nullable=False),
    sa.Column('pide_explicacion', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('activo', sa.Boolean(), server_default=sa.true(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_motivos_rechazo')),
    sa.UniqueConstraint('codigo', name=op.f('uq_motivos_rechazo_codigo'))
    )
    op.create_table('sectores',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=80), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sectores')),
    sa.UniqueConstraint('nombre', name=op.f('uq_sectores_nombre'))
    )
    op.create_table('tipos_dano',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(length=40), nullable=False),
    sa.Column('nombre', sa.String(length=80), nullable=False),
    sa.Column('activo', sa.Boolean(), server_default=sa.true(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tipos_dano')),
    sa.UniqueConstraint('codigo', name=op.f('uq_tipos_dano_codigo'))
    )
    op.create_table('usuarios',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=80), nullable=False),
    sa.Column('correo', sa.String(length=120), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('rol', sa.String(length=20), server_default='ciudadano', nullable=False),
    sa.Column('activo', sa.Boolean(), server_default=sa.true(), nullable=False),
    sa.Column('acepto_privacidad_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint("rol IN ('ciudadano', 'moderador', 'coordinador')", name=op.f('ck_usuarios_rol_valido')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_usuarios'))
    )
    op.create_index('uq_usuarios_correo_lower', 'usuarios', [sa.literal_column('lower(correo)')], unique=True)
    op.create_table('colonias',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('sector_id', sa.Integer(), nullable=False),
    sa.Column('activa', sa.Boolean(), server_default=sa.true(), nullable=False),
    sa.Column('lat', sa.Float(), nullable=True),
    sa.Column('lon', sa.Float(), nullable=True),
    sa.Column('fuente', sa.String(length=200), nullable=True),
    sa.ForeignKeyConstraint(['sector_id'], ['sectores.id'], name=op.f('fk_colonias_sector_id_sectores')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_colonias')),
    sa.UniqueConstraint('sector_id', 'nombre', name=op.f('uq_colonias_sector_id_nombre'))
    )
    op.create_index(op.f('ix_colonias_sector_id'), 'colonias', ['sector_id'], unique=False)
    op.create_table('reportes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('folio', sa.String(length=20), nullable=False),
    sa.Column('categoria', sa.String(length=20), nullable=False),
    sa.Column('tipo_dano_id', sa.Integer(), nullable=True),
    sa.Column('autor_id', sa.Integer(), nullable=False),
    sa.Column('colonia_id', sa.Integer(), nullable=False),
    sa.Column('calle', sa.String(length=150), nullable=False),
    sa.Column('lat', sa.Float(), nullable=False),
    sa.Column('lon', sa.Float(), nullable=False),
    sa.Column('descripcion', sa.String(length=500), nullable=True),
    sa.Column('severidad', sa.String(length=10), nullable=True),
    sa.Column('tamano', sa.String(length=10), nullable=True),
    sa.Column('profundidad', sa.String(length=10), nullable=True),
    sa.Column('carril', sa.String(length=10), nullable=True),
    sa.Column('senalizado', sa.Boolean(), nullable=True),
    sa.Column('fecha_reparacion', sa.Date(), nullable=True),
    sa.Column('nivel_agua', sa.String(length=20), nullable=True),
    sa.Column('hay_riesgo', sa.Boolean(), nullable=True),
    sa.Column('vigente_hasta', sa.DateTime(timezone=True), nullable=True),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('confirmaciones', sa.Integer(), server_default='0', nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('motivo_rechazo_id', sa.Integer(), nullable=True),
    sa.Column('motivo_texto', sa.String(length=500), nullable=True),
    sa.CheckConstraint("(categoria = 'bache' AND tipo_dano_id IS NOT NULL AND severidad IS NOT NULL AND nivel_agua IS NULL AND hay_riesgo IS NULL AND vigente_hasta IS NULL AND estado IN ('recibido', 'validado', 'en_reparacion', 'reparado', 'rechazado') AND ((estado = 'reparado' AND fecha_reparacion IS NOT NULL) OR (estado <> 'reparado' AND fecha_reparacion IS NULL))) OR (categoria = 'encharcamiento' AND tipo_dano_id IS NULL AND severidad IS NULL AND tamano IS NULL AND profundidad IS NULL AND carril IS NULL AND senalizado IS NULL AND fecha_reparacion IS NULL AND nivel_agua IS NOT NULL AND vigente_hasta IS NOT NULL AND estado IN ('activo', 'historico', 'rechazado') AND (nivel_agua <> 'intransitable' OR hay_riesgo IS NOT NULL))", name=op.f('ck_reportes_campos_por_categoria')),
    sa.CheckConstraint("carril IS NULL OR carril IN ('orilla', 'izquierdo', 'derecho', 'varios')", name=op.f('ck_reportes_carril_valido')),
    sa.CheckConstraint("categoria IN ('bache', 'encharcamiento')", name=op.f('ck_reportes_categoria_valida')),
    sa.CheckConstraint("nivel_agua IS NULL OR nivel_agua IN ('a_un_lado', 'cubre_carril', 'media_llanta', 'intransitable')", name=op.f('ck_reportes_nivel_agua_valido')),
    sa.CheckConstraint("profundidad IS NULL OR profundidad IN ('baja', 'media', 'alta')", name=op.f('ck_reportes_profundidad_valida')),
    sa.CheckConstraint("severidad IS NULL OR severidad IN ('baja', 'media', 'alta')", name=op.f('ck_reportes_severidad_valida')),
    sa.CheckConstraint("tamano IS NULL OR tamano IN ('chico', 'mediano', 'grande')", name=op.f('ck_reportes_tamano_valido')),
    sa.CheckConstraint('confirmaciones >= 0', name=op.f('ck_reportes_confirmaciones_no_negativas')),
    sa.CheckConstraint('descripcion IS NULL OR length(descripcion) <= 500', name=op.f('ck_reportes_descripcion_max')),
    sa.ForeignKeyConstraint(['autor_id'], ['usuarios.id'], name=op.f('fk_reportes_autor_id_usuarios')),
    sa.ForeignKeyConstraint(['colonia_id'], ['colonias.id'], name=op.f('fk_reportes_colonia_id_colonias')),
    sa.ForeignKeyConstraint(['motivo_rechazo_id'], ['motivos_rechazo.id'], name=op.f('fk_reportes_motivo_rechazo_id_motivos_rechazo')),
    sa.ForeignKeyConstraint(['tipo_dano_id'], ['tipos_dano.id'], name=op.f('fk_reportes_tipo_dano_id_tipos_dano')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_reportes')),
    sa.UniqueConstraint('folio', name=op.f('uq_reportes_folio'))
    )
    op.create_index(op.f('ix_reportes_autor_id'), 'reportes', ['autor_id'], unique=False)
    op.create_index('ix_reportes_categoria_estado', 'reportes', ['categoria', 'estado'], unique=False)
    op.create_index('ix_reportes_colonia_id', 'reportes', ['colonia_id'], unique=False)
    op.create_index('ix_reportes_creado_en', 'reportes', ['creado_en'], unique=False)
    op.create_index('ix_reportes_lat_lon', 'reportes', ['lat', 'lon'], unique=False)
    op.create_table('usuario_colonias',
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('colonia_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['colonia_id'], ['colonias.id'], name=op.f('fk_usuario_colonias_colonia_id_colonias'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_usuario_colonias_usuario_id_usuarios'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('usuario_id', 'colonia_id', name=op.f('pk_usuario_colonias'))
    )
    op.create_table('confirmaciones',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('reporte_id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint("tipo IN ('confirma', 'sigue', 'ya_no_hay')", name=op.f('ck_confirmaciones_tipo_valido')),
    sa.ForeignKeyConstraint(['reporte_id'], ['reportes.id'], name=op.f('fk_confirmaciones_reporte_id_reportes'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_confirmaciones_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_confirmaciones')),
    sa.UniqueConstraint('reporte_id', 'usuario_id', name=op.f('uq_confirmaciones_reporte_id_usuario_id'))
    )
    op.create_table('historial_estados',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('reporte_id', sa.Integer(), nullable=False),
    sa.Column('estado_anterior', sa.String(length=20), nullable=True),
    sa.Column('estado_nuevo', sa.String(length=20), nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=True),
    sa.Column('comentario', sa.String(length=500), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['usuarios.id'], name=op.f('fk_historial_estados_actor_id_usuarios')),
    sa.ForeignKeyConstraint(['reporte_id'], ['reportes.id'], name=op.f('fk_historial_estados_reporte_id_reportes'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_historial_estados'))
    )
    op.create_index(op.f('ix_historial_estados_reporte_id'), 'historial_estados', ['reporte_id'], unique=False)
    op.create_table('notificaciones',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('reporte_id', sa.Integer(), nullable=False),
    sa.Column('mensaje', sa.String(length=300), nullable=False),
    sa.Column('leida', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['reporte_id'], ['reportes.id'], name=op.f('fk_notificaciones_reporte_id_reportes'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_notificaciones_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notificaciones'))
    )
    op.create_index(op.f('ix_notificaciones_usuario_id'), 'notificaciones', ['usuario_id'], unique=False)

    if es_postgresql():
        op.execute(TRIGGER_CREADO_EN)
        op.execute(TRIGGER_HISTORIAL)


def downgrade() -> None:
    if es_postgresql():
        # Borrar una tabla quita sus triggers, pero no las funciones: se quitan explícitamente para dejar la base limpia
        op.execute("DROP TRIGGER IF EXISTS historial_solo_insercion ON historial_estados")
        op.execute("DROP FUNCTION IF EXISTS historial_solo_insercion()")
        op.execute("DROP TRIGGER IF EXISTS reportes_creado_en_fijo ON reportes")
        op.execute("DROP FUNCTION IF EXISTS reportes_creado_en_fijo()")
    op.drop_index(op.f('ix_notificaciones_usuario_id'), table_name='notificaciones')
    op.drop_table('notificaciones')
    op.drop_index(op.f('ix_historial_estados_reporte_id'), table_name='historial_estados')
    op.drop_table('historial_estados')
    op.drop_table('confirmaciones')
    op.drop_table('usuario_colonias')
    op.drop_index('ix_reportes_lat_lon', table_name='reportes')
    op.drop_index('ix_reportes_creado_en', table_name='reportes')
    op.drop_index('ix_reportes_colonia_id', table_name='reportes')
    op.drop_index('ix_reportes_categoria_estado', table_name='reportes')
    op.drop_index(op.f('ix_reportes_autor_id'), table_name='reportes')
    op.drop_table('reportes')
    op.drop_index(op.f('ix_colonias_sector_id'), table_name='colonias')
    op.drop_table('colonias')
    op.drop_index('uq_usuarios_correo_lower', table_name='usuarios')
    op.drop_table('usuarios')
    op.drop_table('tipos_dano')
    op.drop_table('sectores')
    op.drop_table('motivos_rechazo')
    op.drop_table('folio_contadores')
