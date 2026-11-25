# Liebre Urbana — contexto del proyecto

Proyecto final de Programación Web (AEB-1055, ITCJ). Equipo de 2 estudiantes: Luis Reyna (`luisreyna060318-alt`) y Carlos
Limones (`LimonesCarlos`). Plataforma ciudadana de baches y encharcamientos de Ciudad Juárez (cliente ficticio: A.C.
"Calles Seguras Juárez"), hecha como SPA + API REST. Entrega y demo: jueves 26 de noviembre de 2026, 17:00 (`v1.0.0`).

## El repositorio es PÚBLICO
**Nunca** escribas secretos en un archivo, commit, PR, issue o mensaje: ni contraseñas reales, ni `SECRET_KEY`, ni cadenas de
conexión de Neon (`postgresql://usuario:clave@...`), ni llaves de API. `.env` está ignorado; `.env.example` solo lleva valores de
ejemplo y contraseñas de demostración ficticias. Las claves reales viven solo en los paneles de Render, Vercel y Neon.
Antes de cada commit revisa `git status` y `git diff --cached`.

## Quién hace qué (límites para asistentes y agentes)
- **Los agentes y asistentes NO hacen `git push`, NO abren ni fusionan pull requests y NO suben nada al repositorio de la
  organización sin una orden expresa de Luis.** Commits locales sí, cuando Luis los pide.
- Neon, Render y Vercel (crear, variables, desplegar) solo con aviso previo a Luis. Las claves nunca se imprimen en el chat.
- Nadie fusiona su propio PR: lo aprueba la otra persona del equipo.
- Solo Luis crea migraciones de Alembic (así nunca hay dos "heads"); Carlos las pide por mensaje.

## Stack (no cambiar)
- Frontend: React + TypeScript (Vite), `react-router`, `fetch` con un hook propio `useApi` (sin librerías de estado), CSS externo
  (Flexbox/Grid). Pruebas con Vitest.
- Backend: Python 3.12 + FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL. Pruebas con `pytest` (SQLite en memoria).
- Infra: Docker, Docker Compose, GitHub Actions. Despliegue: Vercel (frontend) + Render (backend, en Docker) + Neon (BD).

## Estructura (monorepo)
```
frontend/   Vite + React · src/{paginas,componentes,api,hooks,estilos} · Dockerfile · nginx.conf · vercel.json
backend/    app/{routers,services,models,schemas,core} · tests/ · Dockerfile · entrypoint.sh · requirements*.txt
db/         alembic.ini · migrations/ · seed.py · datos/ (catálogo de colonias y su fuente)
infra/      docker-compose.yml · DEPLOY.md
docs/       plan/ (fuente de verdad) · ai/ (bitácoras de IA)
raíz        compose.yaml · .env.example · render.yaml · ruff.toml · .github/workflows/ci.yml · AI_USAGE.md · README.md
```
- Compose se usa desde la raíz: `cp .env.example .env` y `docker compose up --build` (frontend en :8080, backend en :8000).
- El Dockerfile del backend se construye desde la **raíz** (necesita `backend/` y `db/`); el del frontend, con `frontend/` como
  contexto. Al arrancar, el contenedor del backend corre `alembic upgrade head` y la semilla si `SEED_ON_START=true`.
- Variables del backend: `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `ENTORNO`, `SEED_ON_START`, `SEED_*_PASSWORD`.
  Del frontend (en tiempo de build): `VITE_API_URL`.

## Reglas de código
- Los estudiantes deben poder EXPLICAR todo: código simple y directo, sin patrones avanzados ni abstracciones innecesarias.
  Comentarios breves en español que expliquen el porqué.
- Capas: router (HTTP, sin lógica) → service (reglas de negocio) → model (SQLAlchemy). Esquemas Pydantic distintos para
  entrada y salida. Nunca devolver `password_hash`; los esquemas públicos **nunca** incluyen al autor de un reporte (RN-04).
- Códigos HTTP correctos (200/201/204/400/401/403/404/409/422/429/503). Errores JSON con la forma del contrato de la API.
- Autorización por rol SIEMPRE en el servidor (dependencia `require_role`); ocultar un botón no es seguridad.
- Contraseñas con `bcrypt`, JWT con `PyJWT`. NO usar `passlib` ni `python-jose` (sin mantenimiento).
- Configuración por variables de entorno (`.env`, nunca en el repo). CORS limitado al dominio del frontend (nunca `*`).
- Consultas con parámetros de SQLAlchemy; nada de SQL armado a mano con texto del usuario.
- Fechas en UTC en la base; se muestran con la zona `America/Ciudad_Juarez`. Las reglas con valores (30 m, 6 h, 10 por hora…)
  viven en `backend/app/core/reglas.py`; el frontend las pide a `GET /api/reglas`.
- Dependencias: solo paquetes conocidos y activos. Antes de agregar uno nuevo, avisar y justificar (OWASP A03).
- Interfaz y mensajes en español de México. HTML semántico, `label` en formularios, texto alternativo, desde 360 px y con teclado.
- Todo estado de pantalla con carga, error y vacío. Datos de ejemplo siempre FICTICIOS (salvo el catálogo oficial de colonias).
- Estilo: `ruff check backend db` (ruff.toml: línea de 120, reglas E, F, I, B) y `npm run lint` en el frontend.

## Fuente de verdad
`docs/plan/`: `PLAN_DE_TRABAJO.md` (reparto, flujo de Git, despliegue), `BACKLOG.md` (historias HU-xx.x con sus CA),
`CONTRATO_API.md` (formas exactas de peticiones y respuestas), `DISENO_TECNICO.md` (modelo de datos, reglas RN-xx, seguridad,
variables de entorno) y `CHECKLIST_ENTREGA.md` (rúbrica). Si algo del código contradice esos documentos, se corrige uno de los
dos en un PR pequeño y se avisa; no se improvisa.

## Commits y flujo de Git
- Conventional Commits en español: `feat(reportes): detecta duplicados a 30 m`, `fix:`, `docs:`, `test:`, `chore:`, `ci:`.
- `main` solo recibe cambios por pull request (salvo el primer commit). Un PR es una historia, menos de 400 líneas, el ID en la
  descripción (`HU-02.3`) y CI en verde. Se fusiona con "merge commit" (no squash) después de que lo apruebe la otra persona.
- Ramas: `feature/<id>-<tema>`. Cada quien hace commits con su propia cuenta.

## Uso de IA (declarado en `AI_USAGE.md`)
- Los commits con código generado por IA terminan con `Co-Authored-By: <modelo real>` (o `Assisted-by:`).
- Cada integrante lleva su bitácora de prompts en `docs/ai/bitacora-<nombre>.md`; se consolidan en `AI_USAGE.md` al final.
- Nunca pegues en un asistente contraseñas, cadenas de conexión ni llaves reales. Los datos de demostración son ficticios.
