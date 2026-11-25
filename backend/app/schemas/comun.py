"""Esquemas comunes: paginación, errores y reglas."""

from pydantic import BaseModel, Field


class Pagina[T](BaseModel):
    """Respuesta de todos los listados paginados: {"items", "total", "pagina", "tam"}."""

    items: list[T]
    total: int = Field(description="Total de resultados de toda la consulta, no solo de esta página")
    pagina: int
    tam: int


class ErrorRespuesta(BaseModel):
    """Forma de TODOS los errores de la API (se usa para documentarlos en /docs)."""

    detail: str = Field(examples=["Revisa los datos marcados"])
    codigo: str = Field(examples=["VALIDACION"])
    campos: dict[str, str] | None = Field(
        default=None, examples=[{"password": "La contraseña debe tener al menos 8 caracteres, con letras y números"}]
    )


class ReglasSalida(BaseModel):
    """Valores de las reglas de negocio que el frontend usa para validar igual que el servidor."""

    radio_duplicado_bache_m: int
    radio_duplicado_encharcamiento_m: int
    vigencia_encharcamiento_horas: int
    desmentidos_para_cerrar: int
    radio_zona_km: int
    max_reportes_por_hora: int
    descripcion_max: int
    password_min: int
    inactividad_min: int
    tam_pagina_consulta: int
    tam_pagina_mis_reportes: int
    umbral_lluvia_pct: int
    zona_horaria: str


def respuestas_error(*codigos: int) -> dict:
    """Atajo para documentar en /docs los errores de un endpoint: responses=respuestas_error(401, 403)."""
    descripciones = {
        401: "Sin sesión, sesión vencida o credenciales incorrectas",
        403: "El rol no alcanza o la cuenta está suspendida",
        404: "No existe",
        409: "Conflicto con datos existentes",
        422: "Datos inválidos (con `campos`)",
    }
    return {c: {"model": ErrorRespuesta, "description": descripciones.get(c, "Error")} for c in codigos}
