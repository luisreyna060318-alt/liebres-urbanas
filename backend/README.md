# Backend (FastAPI)

API REST de Liebre Urbana. Capas: **routers** (HTTP, sin lógica) → **services** (reglas de negocio) → **models**
(SQLAlchemy 2). Los esquemas Pydantic de entrada y de salida son distintos; ninguna salida incluye `password_hash`.

```
backend/
├── app/
│   ├── core/       config, database, reglas (todas las cifras), errores, security, deps, tiempo, geo, paginacion
│   ├── models/     tablas: catalogos.py, usuario.py, reporte.py
│   ├── schemas/    entrada y salida (auth, catalogos, comun, geo, reportes + serializadores)
│   ├── services/   auth, folios, estados (máquina de estados + historial), catalogos, geocodificacion,
│   │               validaciones, reportes, cercanos, confirmaciones, encharcamientos
│   ├── routers/    sistema (/health, /reglas), auth, catalogos, geo, reportes
│   └── main.py     aplicación, CORS, cabeceras de seguridad y manejadores de errores
└── tests/          pytest con SQLite en memoria (sin Docker)
```

## Preparar el entorno (una sola vez)

Requisitos: Python 3.12. Desde la **raíz del repositorio** (Git Bash):

```bash
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
```

## Variables de entorno

| Variable | Para qué | En desarrollo |
|---|---|---|
| `DATABASE_URL` | Cadena de conexión (`postgresql://...` o `postgresql+psycopg://...`) | `postgresql+psycopg://liebre:liebre@127.0.0.1:5432/liebre_urbana` |
| `SECRET_KEY` | Firma de los JWT | Trae una clave de ejemplo; **en producción el backend no arranca con ella** |
| `CORS_ORIGINS` | Dominios del frontend, separados por comas | `http://localhost:5173` |
| `ENTORNO` | `desarrollo` o `produccion` | `desarrollo` |
| `SEED_CIUDADANO_PASSWORD`, `SEED_MODERADOR_PASSWORD`, `SEED_COORDINADOR_PASSWORD` | Contraseñas de las cuentas de demostración | Opcionales (ver abajo); obligatorias en producción |

Se leen del entorno o del archivo `.env` de la raíz (que **nunca** se sube). Clave segura para producción:
`python -c "import secrets; print(secrets.token_urlsafe(48))"`.

## Base de datos: migrar y sembrar

Con un PostgreSQL corriendo y `DATABASE_URL` apuntando a él (desde la raíz):

```bash
backend/.venv/Scripts/alembic.exe -c db/alembic.ini upgrade head     # crea las 11 tablas y los triggers
backend/.venv/Scripts/python.exe db/seed.py                          # catálogos, cuentas, colonias y 500 reportes de demostración
backend/.venv/Scripts/alembic.exe -c db/alembic.ini downgrade base   # (opcional) deshace todo
```

La semilla es idempotente: puede correrse varias veces y solo agrega lo que falta. Corre en este orden: catálogos,
cuentas de demostración, colonias (desde `db/datos/colonias_juarez.csv`; si falta, termina con un mensaje claro) y
500 reportes ficticios en las últimas 12 semanas (siempre los mismos, semilla fija; solo se cargan si la tabla de
reportes está vacía). También crea 30 cuentas ciudadanas ficticias (`ciudadano01@liebreurbana.test` ... `30`) cuya
contraseña es aleatoria y desconocida: no sirven para entrar. Las pruebas usan colonias inventadas de
`backend/tests/datos/`, no el catálogo real.

### Cuentas de demostración (datos ficticios)

| Rol | Correo |
|---|---|
| ciudadano | `ciudadano@liebreurbana.test` |
| moderador | `moderador@liebreurbana.test` |
| coordinador | `coordinador@liebreurbana.test` |

En desarrollo, si no se definen las variables `SEED_*_PASSWORD`, las tres usan la contraseña de demostración
**`LiebreDemo2026`**. Es pública y solo sirve para la demo: no la uses en ningún otro lado. En producción la semilla
exige las variables.

## Arrancar la API

```bash
cd backend
.venv/Scripts/uvicorn.exe app.main:app --reload
```

Documentación interactiva en <http://127.0.0.1:8000/docs>. Para las rutas protegidas: `POST /api/auth/login`,
copia `access_token` y pégalo en **Authorize**.

## Pruebas y estilo

```bash
cd backend && .venv/Scripts/python.exe -m pytest -q        # SQLite en memoria, sin Docker
cd .. && backend/.venv/Scripts/ruff.exe check backend db  # usa el ruff.toml de la raíz
```

## Reglas que conviene conocer antes de programar otro PR

- **Cifras**: todas en `app/core/reglas.py` (y públicas en `GET /api/reglas`). No repitas números en otro lado.
- **Errores**: lanza `ErrorApi(status, "CODIGO", "mensaje")` desde el servicio; la respuesta sale con la forma
  `{detail, codigo, campos}` del contrato. Para errores por campo: `error_validacion({"campo": "mensaje"})`.
- **Autorización**: `Depends(require_role("moderador", "coordinador"))`. `usuario_actual` relee al usuario de la base
  en cada petición (el cambio de rol o la suspensión surten efecto de inmediato).
- **Estados**: cambia el estado SOLO con `services.estados.registrar_cambio_estado(...)`; al crear un reporte usa
  `registrar_estado_inicial(...)`. Ambas hacen `flush`, el `commit` lo hace quien llama.
- **Folios**: `services.folios.generar_folio(db, prefijo_de(categoria), hoy_local().year)` antes del commit.
- **Fechas**: guarda y devuelve UTC (`core.tiempo.ahora_utc()`); para "qué día es hoy en Juárez", `hoy_local()`.
- **Cercanía**: prefiltra con `core.geo.caja()` en SQL y confirma con `core.geo.distancia_m()`.
- **Municipio (RN-01)**: `core.geo.dentro_del_municipio(lat, lon)` con el rectángulo `MUNICIPIO_BBOX` de `reglas.py`
  (fuente anotada ahí). Funciona sin internet.
- **Nominatim**: solo `services/geocodificacion.py` sale a internet (1 petición por segundo, caché, 5 s, 503 si
  falla). En las pruebas la red está bloqueada por el fixture `sin_red` de `conftest.py`: simúlala con
  `monkeypatch.setattr(geocodificacion, "_llamar_http", falso)` (ver `tests/test_geo.py`).
- **Historial**: solo se inserta. El ORM lanza `HistorialInalterable` si se intenta modificar o borrar una fila, y en
  PostgreSQL un trigger lo impide. Única excepción: al borrar un reporte completo su historial se va en cascada.
- **Salida de reportes**: arma `ReportePublico`/`ReporteMio`/`Cercano`/`ReporteDetalle` SOLO con los serializadores de
  `schemas/reportes.py` (`a_reporte_publico(reporte, hoy_local())`...). Copian campo por campo: nunca sale el autor (RN-04).
- **Encharcamientos vencidos**: no hay tareas programadas. Llama `services.encharcamientos.expirar_vencidos(db)` al inicio
  de cualquier endpoint que lea encharcamientos (consulta, detalle, zona, tablero).
- **Rutas**: las rutas fijas como `/api/reportes/cercanos` se registran antes que `/api/reportes/{id}`; si agregas
  `GET /api/reportes/{reporte_id}`, declara el id como `int` o incluye tu router después de `routers/reportes.py`.
- **Seguridad**: si agregas un endpoint, súmalo a `ENDPOINTS` en `tests/test_seguridad.py` (una prueba lo exige).
  Revisión A01/A02 en `docs/seguridad-backend.md`.
