"""Modelos de la base de datos. Importar este paquete registra todas las tablas en Base.metadata."""

from app.models.catalogos import Colonia, MotivoRechazo, Sector, TipoDano
from app.models.reporte import (
    Confirmacion,
    FolioContador,
    HistorialEstado,
    HistorialInalterable,
    Notificacion,
    Reporte,
)
from app.models.usuario import Usuario, UsuarioColonia, normalizar_correo

__all__ = [
    "Colonia",
    "Confirmacion",
    "FolioContador",
    "HistorialEstado",
    "HistorialInalterable",
    "MotivoRechazo",
    "Notificacion",
    "Reporte",
    "Sector",
    "TipoDano",
    "Usuario",
    "UsuarioColonia",
    "normalizar_correo",
]
