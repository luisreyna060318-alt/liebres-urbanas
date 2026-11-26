# Liebre Urbana

[![CI](https://github.com/luisreyna060318-alt/liebres-urbanas/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/luisreyna060318-alt/liebres-urbanas/actions/workflows/ci.yml)

Plataforma ciudadana de baches y encharcamientos de Ciudad Juárez. Los vecinos reportan, consultan antes de salir qué calles
conviene evitar cuando llueve y dan seguimiento a la reparación; los voluntarios validan; la mesa directiva presenta cifras.

Proyecto final de **Programación Web (AEB-1055)**, Instituto Tecnológico de Ciudad Juárez, agosto a diciembre de 2026.
El cliente (A.C. "Calles Seguras Juárez") es ficticio y se creó con fines académicos.

> Las 20 historias indispensables están en `main`. Los cambios entran por pull requests con revisión cruzada.

## Integrantes y roles

| Integrante | GitHub | Áreas |
|---|---|---|
| Luis David Reyna Morisco | `luisreyna060318-alt` | Base de datos, backend (autenticación, roles, geocodificación), esqueleto del frontend, Docker, CI y despliegue |
| Carlos Limones Ayala | `LimonesCarlos` | Consulta, moderación, administración y tablero (de punta a punta), accesibilidad y pruebas del frontend |

Cada quien es dueño de sus historias de punta a punta; el reparto completo está en
[docs/plan/PLAN_DE_TRABAJO.md](docs/plan/PLAN_DE_TRABAJO.md).

## Documentación del plan

- [Plan de trabajo](docs/plan/PLAN_DE_TRABAJO.md): alcance, reparto, cronograma, flujo de Git y riesgos
- [Backlog](docs/plan/BACKLOG.md): las 34 historias de usuario con su responsable y prioridad
- [Contrato de la API](docs/plan/CONTRATO_API.md): formas exactas de peticiones y respuestas
- [Diseño técnico](docs/plan/DISENO_TECNICO.md): arquitectura, modelo de datos, endpoints y reglas
- [Checklist de entrega](docs/plan/CHECKLIST_ENTREGA.md): rúbrica y evidencias

## Stack

React + TypeScript (Vite) · FastAPI · PostgreSQL (SQLAlchemy y Alembic) · Docker Compose · GitHub Actions ·
Despliegue en Vercel (frontend), Render (backend) y Neon (base de datos).

## Cómo correr el proyecto

Requiere Docker Desktop encendido.

```
copy .env.example .env
docker compose up --build
```

- Frontend: <http://localhost:8080>
- API y documentación (OpenAPI): <http://localhost:8000/docs>

El primer arranque crea las tablas (migraciones de Alembic) y carga los datos de demostración, que son ficticios.
Si los puertos 8000 u 8080 ya están ocupados, cámbialos en `infra/docker-compose.yml`.

## Usuarios de prueba

Son cuentas de **demostración** (ficticias y públicas, definidas en `.env.example`); no se usan en ningún otro lugar.

| Rol | Correo | Contraseña |
|---|---|---|
| Ciudadano | `ciudadano@liebreurbana.test` | `Demo-Ciudadano-2026` |
| Moderador | `moderador@liebreurbana.test` | `Demo-Moderador-2026` |
| Coordinador | `coordinador@liebreurbana.test` | `Demo-Coordinador-2026` |

## Despliegue público

| Pieza | Servicio | Dirección |
|---|---|---|
| Aplicación (frontend) | Vercel | <https://liebre-urbana.vercel.app> |
| API y documentación OpenAPI | Render (Docker) | <https://liebre-urbana-api.onrender.com/docs> |
| Base de datos | Neon (PostgreSQL 16) | solo accesible desde la API |

Render y Neon son gratuitos y se duermen sin tráfico: la primera petición puede tardar entre 30 y 60 segundos.
El despliegue público usa las mismas cuentas de demostración de la tabla de arriba.
