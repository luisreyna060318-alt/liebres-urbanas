# Imagen del backend (FastAPI). Se construye desde la RAÍZ del repositorio, porque necesita backend/ y db/
# (las migraciones de Alembic y la semilla viven en db/):
#   docker build -f backend/Dockerfile -t liebre-urbana-api .
FROM python:3.12-slim

# PYTHONPATH: así "app" (que vive en backend/) se puede importar también desde db/seed.py y las migraciones
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/backend

# El proceso NO corre como root: si alguien explotara una falla, tendría menos poder dentro del contenedor
RUN useradd --create-home --uid 1000 app

# Se mantiene la misma estructura que en el repositorio (/app/backend y /app/db): así las rutas relativas
# de alembic, de la semilla y de la configuración funcionan igual que en tu computadora.
WORKDIR /app

# Primero solo las dependencias: Docker reutiliza esta capa mientras requirements.txt no cambie
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend/app backend/app
COPY db db
COPY backend/entrypoint.sh /entrypoint.sh
# sed quita los saltos de línea de Windows (\r): con ellos el script no arrancaría en Linux
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh && chown -R app:app /app

USER app
WORKDIR /app/backend
EXPOSE 8000

# Docker marca el contenedor como "healthy" cuando /api/health responde
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=5 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT', '8000'), timeout=3)"

ENTRYPOINT ["/entrypoint.sh"]
