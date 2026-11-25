"""Errores con la forma única de la API (CONTRATO_API, sección 1).

Toda respuesta de error se ve así:
    {"detail": "Mensaje para la persona", "codigo": "ETIQUETA_ESTABLE", "campos": {"password": "..."}}
`campos` solo aparece en los errores de validación (422).

Los servicios lanzan ErrorApi y no saben nada de HTTP más allá del código; los manejadores de abajo
(registrados en main.py) convierten todo, incluidos los errores de Pydantic y de FastAPI, a esa forma.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("liebre")


class ErrorApi(Exception):
    """Error que la API devuelve tal cual. Ejemplo:

    raise ErrorApi(409, "TRANSICION_INVALIDA", "No se puede pasar de recibido a reparado")

    `campos` es para errores de validación por campo; `extra` agrega llaves a la respuesta
    (por ejemplo "duplicados" en POSIBLE_DUPLICADO).
    """

    def __init__(
        self, status_code: int, codigo: str, detail: str, campos: dict | None = None, extra: dict | None = None
    ):
        super().__init__(detail)
        self.status_code = status_code
        self.codigo = codigo
        self.detail = detail
        self.campos = campos
        self.extra = extra or {}


def error_validacion(campos: dict[str, str], detail: str = "Revisa los datos marcados") -> ErrorApi:
    """422 VALIDACION con mensajes por campo, para validaciones que se hacen en los servicios."""
    return ErrorApi(422, "VALIDACION", detail, campos=campos)


def _respuesta(status_code: int, codigo: str, detail: str, campos=None, extra=None, headers=None) -> JSONResponse:
    contenido = {"detail": detail, "codigo": codigo}
    if campos:
        contenido["campos"] = campos
    if extra:
        contenido.update(extra)
    return JSONResponse(status_code=status_code, content=contenido, headers=headers)


# --- Traducción de los errores de Pydantic al español ---------------------------------------------
MENSAJES_PYDANTIC = {
    "missing": "Este campo es obligatorio",
    "string_type": "Debe ser texto",
    "string_too_short": "Debe tener al menos {min_length} caracteres",
    "string_too_long": "Debe tener como máximo {max_length} caracteres",
    "int_type": "Debe ser un número entero",
    "int_parsing": "Debe ser un número entero",
    "int_from_float": "Debe ser un número entero",
    "float_type": "Debe ser un número",
    "float_parsing": "Debe ser un número",
    "bool_type": "Debe ser verdadero o falso",
    "bool_parsing": "Debe ser verdadero o falso",
    "greater_than": "Debe ser mayor que {gt}",
    "greater_than_equal": "Debe ser mayor o igual a {ge}",
    "less_than": "Debe ser menor que {lt}",
    "less_than_equal": "Debe ser menor o igual a {le}",
    "literal_error": "Valor no permitido. Opciones: {expected}",
    "enum": "Valor no permitido. Opciones: {expected}",
    "date_type": "Debe ser una fecha (AAAA-MM-DD)",
    "date_parsing": "Debe ser una fecha (AAAA-MM-DD)",
    "date_from_datetime_parsing": "Debe ser una fecha (AAAA-MM-DD)",
    "datetime_type": "Debe ser una fecha y hora ISO 8601",
    "datetime_parsing": "Debe ser una fecha y hora ISO 8601",
    "json_invalid": "El cuerpo de la petición no es JSON válido",
    "model_type": "Debe ser un objeto JSON",
    "model_attributes_type": "Debe ser un objeto JSON",
    "dict_type": "Debe ser un objeto JSON",
    "list_type": "Debe ser una lista",
    "extra_forbidden": "Campo no permitido",
}


def _mensaje_en_espanol(error: dict) -> str:
    tipo = error.get("type", "")
    ctx = error.get("ctx") or {}
    if tipo == "value_error":
        # Nuestros validadores lanzan ValueError con el mensaje ya en español
        causa = ctx.get("error")
        return str(causa) if causa else "Valor inválido"
    plantilla = MENSAJES_PYDANTIC.get(tipo)
    if plantilla is None:
        return "Valor inválido"
    try:
        return plantilla.format(**ctx)
    except (KeyError, IndexError):
        return plantilla.split(".")[0]


def campos_de_validacion(errores: list[dict]) -> dict[str, str]:
    """{"password": "mensaje", "colonia_id": "mensaje"} con el nombre del campo de la entrada.
    Se ignora el primer elemento de la ubicación ("body", "query", "path"). Un mensaje por campo."""
    campos: dict[str, str] = {}
    for error in errores:
        ubicacion = [str(parte) for parte in error.get("loc", ())]
        if ubicacion and ubicacion[0] in ("body", "query", "path", "header", "cookie"):
            ubicacion = ubicacion[1:]
        nombre = ".".join(ubicacion) or "cuerpo"
        campos.setdefault(nombre, _mensaje_en_espanol(error))
    return campos


# --- Manejadores globales -------------------------------------------------------------------------
MENSAJES_HTTP = {
    401: ("NO_AUTENTICADO", "Inicia sesión para continuar"),
    403: ("SIN_PERMISO", "No tienes permiso para realizar esta acción"),
    404: ("NO_ENCONTRADO", "El recurso no existe"),
    405: ("METODO_NO_PERMITIDO", "Método no permitido en esta ruta"),
}


def registrar_manejadores(app: FastAPI) -> None:
    """Conecta los manejadores de errores a la aplicación (se llama una vez en main.py)."""

    @app.exception_handler(ErrorApi)
    async def manejar_error_api(_request: Request, error: ErrorApi) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if error.status_code == 401 else None
        return _respuesta(error.status_code, error.codigo, error.detail, error.campos, error.extra, headers)

    @app.exception_handler(RequestValidationError)
    async def manejar_validacion(_request: Request, error: RequestValidationError) -> JSONResponse:
        campos = campos_de_validacion(list(error.errors()))
        return _respuesta(422, "VALIDACION", "Revisa los datos marcados", campos)

    @app.exception_handler(StarletteHTTPException)
    async def manejar_http(_request: Request, error: StarletteHTTPException) -> JSONResponse:
        # Errores que genera FastAPI/Starlette (ruta inexistente, método equivocado...): mismo formato, en español
        codigo, mensaje = MENSAJES_HTTP.get(error.status_code, ("ERROR", str(error.detail)))
        return _respuesta(error.status_code, codigo, mensaje, headers=getattr(error, "headers", None))

    @app.exception_handler(Exception)
    async def manejar_inesperado(request: Request, error: Exception) -> JSONResponse:
        # No se devuelve el detalle técnico (podría revelar datos internos); queda en el log del servidor
        log.exception("Error no controlado en %s %s", request.method, request.url.path)
        return _respuesta(500, "ERROR_INTERNO", "Ocurrió un error inesperado. Intenta de nuevo más tarde")
