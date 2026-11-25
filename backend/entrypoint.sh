#!/bin/sh
# Arranque del contenedor del backend:
#   1) crea o actualiza las tablas (migraciones de Alembic),
#   2) opcionalmente carga los datos de demostración (SEED_ON_START=true),
#   3) arranca la API.
set -e

echo "Aplicando migraciones..."
alembic -c /app/db/alembic.ini upgrade head

# La semilla es idempotente: si las tablas ya tienen datos, no los duplica
if [ "${SEED_ON_START:-false}" = "true" ]; then
    echo "Cargando datos de demostración..."
    python /app/db/seed.py
fi

echo "Arrancando la API..."
# PORT lo define Render; en Docker Compose se usa 8000. --proxy-headers: detrás del proxy de Render
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers
