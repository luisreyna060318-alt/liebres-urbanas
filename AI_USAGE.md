# Declaración de uso de IA

Proyecto: Liebre Urbana (Programación Web, AEB-1055). Seguimos la política de autoría de la ACM: el uso de IA generativa está
permitido pero se declara, la IA no es autora y las personas del equipo responden por la exactitud de todo el material, incluido el
que generó la herramienta.

> Estado: **en construcción**. Se completa durante el proyecto y se cierra antes de la etiqueta `v1.0.0`.

## 1. Herramientas y modelos

| Herramienta | Modelo | Quién la usa |
|---|---|---|
| Claude Code (aplicación de escritorio de Claude, pestaña Code): orquestador | Claude Sonnet 5.5 (`claude-sonnet-5-5`) | Luis David Reyna Morisco |
| Agentes de apoyo lanzados por el orquestador (subagentes de Claude Code, cada uno en su propia copia de trabajo de Git) | Se anota el modelo real de cada uno en el trailer `Co-Authored-By` del commit y en la bitácora | Luis David Reyna Morisco |
| Por declarar | Por declarar | Carlos Limones Ayala |

Modelos de los agentes de apoyo (lanzados por el orquestador en Claude Code): Claude Opus 5.5 para el backend (L1 y L6 a L11) y Claude Sonnet 5.5 para el frontend, la infraestructura, la semilla, el catálogo de colonias y los diagramas. Cada commit indica el modelo real en su línea `Co-Authored-By`.

## 2. Harness y modo de uso

- **Luis**: agente que lee y edita archivos y ejecuta comandos en su computadora (Claude Code dentro de la aplicación de escritorio
  de Claude). Las acciones que salen de la computadora (commit, push, pull request, despliegue, descargas) se hacen solo dentro de lo que Luis autoriza de forma expresa.
- **Carlos**: por declarar.

## 3. Archivos de contexto e instrucciones

| Archivo | Para qué sirve | Estado |
|---|---|---|
| `CLAUDE.md` | Stack, estructura, reglas de código y de commits que sigue el asistente | Incluido |
| `docs/plan/` | Plan, backlog, diseño técnico y checklist que sirven de contexto al asistente | Incluido |
| Conectores MCP de Vercel, Render y Neon | El asistente los usa para el despliegue, siempre con aprobación de Luis | Usados el 25-nov para crear y configurar los tres servicios (PR #29) |
| Infraestructura reutilizada de `extra-liebres` (proyecto previo del mismo equipo): Dockerfiles, CI, `render.yaml`, `vercel.json`, patrones de autenticación y del cliente de la API | Adaptada y verificada contra los requerimientos de este proyecto | Incluida |
| Skills y plantillas de prompts | Por declarar si se usan | — |

## 4. Bitácora de prompts significativos

Cada integrante lleva su propia bitácora para evitar choques al fusionar: [Luis](docs/ai/bitacora-luis.md) y
`docs/ai/bitacora-carlos.md` (la crea Carlos). Antes de la etiqueta se consolidan en la tabla de este archivo.

| Fecha | Integrante | Herramienta / modelo | Prompt | Archivos afectados | Ajustes humanos |
|---|---|---|---|---|---|
| 2026-11-24 | Luis | Claude Code / Claude Sonnet 5.5 | Resumen fiel: leer los requerimientos del cliente, las reglas del proyecto final y el manual; proponer un plan de trabajo repartido por igual entre dos personas, con despliegue en Vercel, Render y Neon | `docs/plan/*`, `README.md`, `.gitignore`, `.github/*`, `AI_USAGE.md`, `docs/ai/bitacora-luis.md` | Por completar tras la revisión de Luis |
| 2026-11-24 | Luis | Claude Code / Claude Sonnet 5.5 (orquestador) | Pedir al orquestador que reparta el trabajo de Luis entre agentes de apoyo en paralelo y que abra PRs modulares y apilados para la revisión de Carlos | Ramas y PRs de `liebres-urbanas` | Luis fijó las reglas: PRs revisados por Carlos, nada se fusiona sin su aprobación |
| 2026-11-24 | Luis | Agente de Claude Code / Claude Opus 5.5 | Backend base: API en capas, 11 tablas, migración con triggers, autenticación, roles, catálogos, semilla de catálogos y 91 pruebas (adaptando patrones de `extra-liebres`) | `backend/`, `db/` (PR L1) | Por completar tras la revisión de Luis y Carlos |
| 2026-11-24 | Luis | Agente de Claude Code / Claude Sonnet 5.5 | Frontend base: Vite, React, TypeScript, rutas por rol, componentes, sesión, pantallas de cuenta y 57 pruebas (adaptando patrones de `extra-liebres`) | `frontend/` (PR L2) | Por completar |
| 2026-11-24 | Luis | Agente de Claude Code / Claude Sonnet 5.5 | Docker, Compose, CI de GitHub Actions, `render.yaml`, `vercel.json`, guía de despliegue y `CLAUDE.md` (adaptando `extra-liebres`) | `compose.yaml`, `infra/`, `backend/Dockerfile`, `frontend/Dockerfile`, `.github/workflows/ci.yml`, `render.yaml`, `CLAUDE.md` (PR L3) | Por completar |
| 2026-11-24 | Luis | Agente de Claude Code / Claude Sonnet 5.5 | Descargar el catálogo oficial de asentamientos de Juárez, elegir colonias reales, obtener coordenadas aproximadas y asignar sectores | `db/datos/` (PR L4) | Por completar |
| 2026-11-24 | Luis | Agente de Claude Code / Claude Opus 5.5 | Backend de reportes: geocodificación con Nominatim, alta de baches, duplicados, mis reportes, encharcamientos con vigencia y pruebas de seguridad (235 pruebas nuevas) | `backend/` (PRs L6 a L11) | Por completar |
| 2026-11-24 | Luis | Agente de Claude Code / Claude Sonnet 5.5 | Pantallas de reportar (bache y encharcamiento), duplicados, mis reportes y acciones de confirmación (69 pruebas nuevas) | `frontend/` (PRs L12 a L14) | Por completar |
| 2026-11-25 | Luis | Agente de Claude Code / Claude Sonnet 5.5 | Semilla de 500 reportes ficticios en 12 semanas con historial coherente | `db/seed.py`, `backend/tests/` (PR L5) | Por completar |
| 2026-11-25 | Luis | Agente de Claude Code / Claude Sonnet 5.5 | Diagramas de arquitectura y entidad-relación a partir del código real | `docs/arquitectura.*`, `db/er.*` | Por completar |
| 2026-11-24 | Luis | Claude Code / Claude Sonnet 5.5 | Leer los tres documentos (requerimientos del cliente, reglas del proyecto final, manual) y desarrollar un plan de trabajo detallado para Liebre Urbana: dos personas, trabajo repartido por igual, simplificado pero completo, revisión cruzada de PRs, despliegue con Vercel, Render y Neon | `docs/plan/*`, `README.md`, `.gitignore`, `.github/*`, `AI_USAGE.md` | Por completar tras la revisión de Luis |
| 2026-11-25 | Luis | Agentes de Claude Code / Claude Opus 5.5 y Claude Sonnet 5.5 (revisores, solo lectura) | Revisar los 11 PRs de Carlos (#18 a #28) contra el contrato, los criterios de aceptación, la privacidad y la autorización; el orquestador publicó las revisiones con la cuenta de Luis | Comentarios en los PRs #18 a #28 (sin cambios de código) | Luis autorizó revisar y aprobar; se pidieron cambios en #28 |
| 2026-11-25 | Luis | Claude Code / Claude Sonnet 5.5 (orquestador) | Crear el proyecto en Neon, el servicio en Render y el proyecto en Vercel, configurar variables y CORS, y comprobar el despliegue | Servicios en Neon, Render y Vercel (sin cambios de código) | Luis autorizó crear los tres servicios y aprobó el acceso de Vercel a GitHub; las claves no se escribieron en ningún archivo |
| 2026-11-25 | Luis | Claude Code / Claude Sonnet 5.5 y agente con Claude Opus 5.5 | Redactar el borrador del reporte técnico y de la autoevaluación a partir del repositorio y darles el formato de un reporte previo del equipo (docx y PDF) | `docs/reporte/*`, `docs/REPORTE.docx`, `docs/REPORTE.pdf`, `docs/AUTOEVALUACION.md` (PR #31) | Luis entregó el modelo de formato y el número de control de Carlos; en revisión por Carlos |
| 2026-11-25 | Luis | Claude Code / Claude Sonnet 5.5 (orquestador) | Corregir las observaciones que quedaban de la revisión y comprobar antes de la etiqueta: secretos en el historial y arranque desde un clon limpio | `frontend/`, `docs/plan/CONTRATO_API.md` (PR #35) | Luis pidió las correcciones y autorizó las comprobaciones |
| 2026-11-25 | Luis | Claude Code / Claude Sonnet 5.5 (orquestador) y agente auditor con Claude Opus 5.5 | Registrar el backlog como issues, auditar los criterios de las historias indispensables antes de cerrarlas, corregir los botones de confirmar y desmentir y pedir a Carlos sus textos | Issues #36 a #80, `frontend/` (PR #81) | Luis pidió abrir los issues y cerrar solo lo completo |
| 2026-11-25 | Luis | Claude Code / Claude Sonnet 5.5 (orquestador) | Corregir los huecos que halló la auditoría: severidad y nivel del agua en la lista, filtro por sector en la consulta y rechazo de encharcamientos desde el detalle | `frontend/`, `backend/` (PRs #82 a #84) | Luis pidió corregir los tres |

## 5. Marcado en commits

Los commits con código generado por IA terminan con `Co-Authored-By: <herramienta/modelo>` (lo agrega la herramienta) o
`Assisted-by: <herramienta/modelo>`.

## 6. Estimación por carpeta del código generado por IA

| Carpeta | % aproximado |
|---|---|
| `frontend/` | ~95 % |
| `backend/` | ~95 % |
| `db/` | ~95 % |
| `infra/` | ~95 % |

Estimación aproximada: parte del código se adaptó de código que ya existía (infraestructura y patrones del proyecto previo
`extra-liebres`).

## 7. Reflexión crítica

**Reflexión crítica (Luis).** Lo que más me enseñó fue revisar #24: el código pasaba todas las pruebas, pero leía el reporte sin
bloquear la fila y dos moderadores podían dejar un historial incoherente. Lo dejé como nota no bloqueante, se fusionó así y aprendí
que, si el error toca datos que no se pueden borrar, hay que pedir cambios. En #28 también aprendí a separar "no se hizo" de "no hay
evidencia": pedí corregir la bitácora y resultó que la comparación sí se había hecho, solo faltaba documentarla.

**Reflexión crítica (Carlos).** Pendiente: Carlos la agrega con su propio pull request.

## Reglas de seguridad que seguimos

- Nunca se pegan en un asistente contraseñas, cadenas de conexión ni llaves de API reales. Las claves viven solo en los paneles de
  Render, Vercel y Neon.
- Se revisa que la IA no agregue dependencias inexistentes o abandonadas (riesgo A03 del OWASP Top 10:2025): una dependencia nueva
  se justifica antes de agregarla.
- Los datos de ejemplo son siempre ficticios.
