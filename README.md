# Liebre Urbana

Plataforma ciudadana de baches y encharcamientos de Ciudad Juárez. Los vecinos reportan, consultan antes de salir qué calles
conviene evitar cuando llueve y dan seguimiento a la reparación; los voluntarios validan; la mesa directiva presenta cifras.

Proyecto final de **Programación Web (AEB-1055)**, Instituto Tecnológico de Ciudad Juárez, agosto a diciembre de 2026.
El cliente (A.C. "Calles Seguras Juárez") es ficticio y se creó con fines académicos.

> Estado: **en planeación**. Este README se completa conforme avanza el proyecto.

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

## Pendiente de completar antes de `v1.0.0`

- URL pública del despliegue
- Cómo correr el proyecto con `docker compose up`
- Usuarios de prueba (uno por rol)
- Insignia del CI
