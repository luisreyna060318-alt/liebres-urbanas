"""Punto de entrada de la API. Se arranca (desde backend/) con: uvicorn app.main:app --reload"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errores import registrar_manejadores
from app.routers import admin_catalogos, auth, catalogos, geo, reportes, sistema

app = FastAPI(
    title="Liebre Urbana API",
    description=(
        "API de **Liebre Urbana**, plataforma ciudadana para reportar baches y encharcamientos en Ciudad Juárez.\n\n"
        "- Todas las rutas empiezan con `/api`. Fechas en UTC con `Z`.\n"
        "- Errores: `{\"detail\": \"...\", \"codigo\": \"ETIQUETA\", \"campos\": {...}}` (`campos` solo en 422).\n"
        "- Para las rutas protegidas: entra en `POST /api/auth/login`, copia `access_token` y pégalo en "
        "**Authorize**. El token dura 30 minutos."
    ),
    version="0.1.0",
)

# CORS: el navegador solo deja llamar a la API desde el frontend configurado en CORS_ORIGINS. Nunca "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_lista,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

registrar_manejadores(app)


@app.middleware("http")
async def cabeceras_de_seguridad(request: Request, call_next):
    """Cabeceras que el navegador respeta en TODAS las respuestas (OWASP A02)."""
    respuesta = await call_next(request)
    respuesta.headers["X-Content-Type-Options"] = "nosniff"  # no "adivinar" el tipo de archivo
    respuesta.headers["X-Frame-Options"] = "DENY"  # nadie incrusta la API en otra página
    respuesta.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api"):
        respuesta.headers["Cache-Control"] = "no-store"  # puede haber datos personales: sin caché
    if settings.es_produccion:
        # HSTS: el navegador solo vuelve a entrar por HTTPS (en la laptop se usa http://, por eso solo en producción)
        respuesta.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return respuesta


app.include_router(sistema.router)
app.include_router(auth.router)
app.include_router(catalogos.router)
app.include_router(admin_catalogos.router)
app.include_router(geo.router)
app.include_router(reportes.router)
