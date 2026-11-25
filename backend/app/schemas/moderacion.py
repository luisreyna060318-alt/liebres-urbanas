"""Entradas de moderación (HU-05.1). La salida es ReportePublico: nunca incluye al autor (RN-04)."""

from pydantic import BaseModel, Field, field_validator

from app.core.reglas import COMENTARIO_MAX, DESCRIPCION_MAX


def limpiar_texto(v: str | None) -> str | None:
    """Quita espacios sobrantes; un texto vacío cuenta como "sin texto"."""
    if v is None:
        return None
    return v.strip() or None


class ValidarEntrada(BaseModel):
    """POST /api/reportes/{id}/validar."""

    comentario: str | None = Field(
        default=None, max_length=COMENTARIO_MAX, examples=["Confirmado con fotos de la cuadra"],
        description=f"Opcional y público (aparece en el historial), hasta {COMENTARIO_MAX} caracteres",
    )

    @field_validator("comentario")
    @classmethod
    def limpiar(cls, v: str | None) -> str | None:
        return limpiar_texto(v)


class RechazarEntrada(BaseModel):
    """POST /api/reportes/{id}/rechazar. Si el motivo tiene pide_explicacion, `motivo_texto` es obligatorio
    (lo valida el servicio, porque depende del motivo elegido)."""

    motivo_rechazo_id: int = Field(examples=[5], description="Motivo activo de GET /api/motivos-rechazo")
    motivo_texto: str | None = Field(
        default=None, max_length=DESCRIPCION_MAX, examples=["El punto está dentro de un estacionamiento privado"],
        description="Explicación para el autor; obligatoria si el motivo la pide (por ejemplo «Otro»)",
    )
    comentario: str | None = Field(
        default=None, max_length=COMENTARIO_MAX, description="Opcional y público (aparece en el historial)"
    )

    @field_validator("motivo_texto", "comentario")
    @classmethod
    def limpiar(cls, v: str | None) -> str | None:
        return limpiar_texto(v)
