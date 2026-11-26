# Declaración de uso de IA

Proyecto: Liebre Urbana (Programación Web, AEB-1055). Seguimos la política de autoría de la ACM: el uso de IA generativa está
permitido pero se declara, la IA no es autora y las personas del equipo responden por la exactitud de todo el material, incluido el
que generó la herramienta.

> Estado: actualizado el 26 de noviembre de 2026; se cierra con la etiqueta `v1.0.0`.

## 1. Herramientas y modelos

| Herramienta | Modelo | Quién la usa |
|---|---|---|
| Claude Code (aplicación de escritorio de Claude, pestaña Code): orquestador | Claude Sonnet 5.5 (`claude-sonnet-5-5`) | Luis David Reyna Morisco |
| Agentes de apoyo lanzados por el orquestador (subagentes de Claude Code, cada uno en su propia copia de trabajo de Git) | Se anota el modelo real de cada uno en el trailer `Co-Authored-By` del commit y en la bitácora | Luis David Reyna Morisco |
| Claude Code (aplicación de escritorio de Claude, pestaña Code): orquestador | Claude Sonnet 5.5 (`claude-sonnet-5-5`) | Carlos Limones Ayala |
| Subagentes de Claude Code (cada uno en su propia copia de trabajo de Git) | Claude Opus 5.5 y Claude Sonnet 5.5; el modelo real de cada uno va en el trailer `Co-Authored-By` del commit y en la bitácora | Carlos Limones Ayala |

Modelos de los agentes de apoyo (lanzados por el orquestador en Claude Code): Claude Opus 5.5 para el backend (L1 y L6 a L11) y Claude Sonnet 5.5 para el frontend, la infraestructura, la semilla, el catálogo de colonias y los diagramas. Cada commit indica el modelo real en su línea `Co-Authored-By`.

Modelos de los subagentes de Carlos: Claude Opus 5.5 para la consulta y el detalle (C3 y C4), moderación y avance (C6 y C7), el tablero (C10), los arreglos de backend (#34) y la auditoría de seguridad; Claude Sonnet 5.5 para la zona (C5), la administración de colonias y usuarios (C8 y C9), el aviso de lluvia (C11), los arreglos de frontend (#33) y la auditoría de accesibilidad.

## 2. Harness y modo de uso

- **Luis**: agente que lee y edita archivos y ejecuta comandos en su computadora (Claude Code dentro de la aplicación de escritorio
  de Claude). Las acciones que salen de la computadora (commit, push, pull request, despliegue, descargas) se hacen solo dentro de lo que Luis autoriza de forma expresa.
- **Carlos**: agente que lee y edita archivos y ejecuta comandos en su computadora (Claude Code dentro de la aplicación de escritorio de Claude) y que
  lanza subagentes, cada uno en su propia copia de trabajo de Git. Los subagentes solo hacen commits locales: no empujan ramas ni abren PRs. El
  orquestador revisa el diff de cada rama, corre las pruebas, empuja y abre el PR. Carlos autorizó ese flujo, las revisiones de los PRs de Luis, la descarga
  de las herramientas de auditoría (axe y Lighthouse, fuera del repositorio) y que se fusionen sus PRs solo después de la aprobación de Luis; los PRs de
  Luis los fusiona Luis. Las contraseñas y cadenas de conexión de la base local se leen de un `.env` ignorado por Git y no se imprimen; los sitios
  desplegados solo se consultan en solo lectura y sin iniciar sesión.

## 3. Archivos de contexto e instrucciones

| Archivo | Para qué sirve | Estado |
|---|---|---|
| `CLAUDE.md` | Stack, estructura, reglas de código y de commits que sigue el asistente | Incluido |
| `docs/plan/` | Plan, backlog, diseño técnico y checklist que sirven de contexto al asistente | Incluido |
| Conectores MCP de Vercel, Render y Neon | El asistente los usa para el despliegue, siempre con aprobación de Luis | Usados el 25-nov para crear y configurar los tres servicios (PR #29) |
| Infraestructura reutilizada de `extra-liebres` (proyecto previo del mismo equipo): Dockerfiles, CI, `render.yaml`, `vercel.json`, patrones de autenticación y del cliente de la API | Adaptada y verificada contra los requerimientos de este proyecto | Incluida |
| Skill `anthropic-skills:docx` de Claude Code (Luis) | Trabajar el formato del reporte en Word; Luis no usó plantillas de prompts propias | Usada el 25-nov (PR #31) |
| Navegador integrado de la aplicación de Claude (MCP `Claude_Browser`, Luis) | Probar la aplicación en el navegador | Usado el 24 y el 25-nov |
| Instrucciones comunes a los subagentes de Carlos (archivo temporal fuera del repositorio) | Stack, privacidad, `git` sin `push` ni PRs, cómo verificar y qué incluir en el informe de cada subagente | No incluido en el repositorio |
| Navegador integrado de la aplicación de Claude (MCP `Claude_Browser`, Carlos) | Probar la aplicación en el navegador (login por rol, tablero, formularios y vistas en móvil) y comprobar el foco del teclado | Usado el 25 y el 26-nov |
| Skills y plantillas de prompts (Carlos) | Ninguna: Carlos trabajó solo con las instrucciones de `CLAUDE.md` y las comunes a los subagentes | — |

## 4. Bitácora de prompts significativos

Cada integrante lleva su propia bitácora para evitar choques al fusionar: [Luis](docs/ai/bitacora-luis.md) y
`docs/ai/bitacora-carlos.md`. Antes de la etiqueta se consolidan en la tabla de este archivo.

| Fecha | Integrante | Herramienta / modelo | Prompt | Archivos afectados | Ajustes humanos |
|---|---|---|---|---|---|
| 2026-11-24 | Luis | Claude Code / Claude Sonnet 5.5 | Resumen fiel: leer los requerimientos del cliente, las reglas del proyecto final y el manual; proponer un plan de trabajo repartido por igual entre dos personas, con despliegue en Vercel, Render y Neon | `docs/plan/*`, `README.md`, `.gitignore`, `.github/*`, `AI_USAGE.md`, `docs/ai/bitacora-luis.md` | Luis precisó que la entrega es a las 17:00 y decidió trabajar en un repositorio personal, subir a la organización al final, reutilizar `extra-liebres` como parte de su trabajo y asumir más carga la primera noche |
| 2026-11-24 | Luis | Claude Code / Claude Sonnet 5.5 (orquestador) | Pedir al orquestador que reparta el trabajo de Luis entre agentes de apoyo en paralelo y que abra PRs modulares y apilados para la revisión de Carlos | Ramas y PRs de `liebres-urbanas` | Luis fijó las reglas: PRs revisados por Carlos, nada se fusiona sin su aprobación |
| 2026-11-24 | Luis | Agente de Claude Code / Claude Opus 5.5 | Backend base: API en capas, 11 tablas, migración con triggers, autenticación, roles, catálogos, semilla de catálogos y 91 pruebas (adaptando patrones de `extra-liebres`) | `backend/`, `db/` (PR L1) | Sin cambios manuales de Luis al código. Carlos aprobó el PR #1 tras correr pytest, ruff y la migración en PostgreSQL; Luis pidió las fusiones |
| 2026-11-24 | Luis | Agente de Claude Code / Claude Sonnet 5.5 | Frontend base: Vite, React, TypeScript, rutas por rol, componentes, sesión, pantallas de cuenta y 57 pruebas (adaptando patrones de `extra-liebres`) | `frontend/` (PR L2) | Sin cambios manuales de Luis al código. Carlos aprobó el PR #2 tras correr lint, las 57 pruebas y el build |
| 2026-11-24 | Luis | Agente de Claude Code / Claude Sonnet 5.5 | Docker, Compose, CI de GitHub Actions, `render.yaml`, `vercel.json`, guía de despliegue y `CLAUDE.md` (adaptando `extra-liebres`) | `compose.yaml`, `infra/`, `backend/Dockerfile`, `frontend/Dockerfile`, `.github/workflows/ci.yml`, `render.yaml`, `CLAUDE.md` (PR L3) | Sin cambios manuales de Luis al código. Carlos aprobó el PR #3; después Luis pidió proteger `main` y exigir el CI en verde |
| 2026-11-24 | Luis | Agente de Claude Code / Claude Sonnet 5.5 | Descargar el catálogo oficial de asentamientos de Juárez, elegir colonias reales, obtener coordenadas aproximadas y asignar sectores | `db/datos/` (PR L4) | Sin cambios manuales de Luis al código. Quedaron 23 colonias reales con su fuente; Carlos aprobó el PR #16 |
| 2026-11-24 | Luis | Agente de Claude Code / Claude Opus 5.5 | Backend de reportes: geocodificación con Nominatim, alta de baches, duplicados, mis reportes, encharcamientos con vigencia y pruebas de seguridad (235 pruebas nuevas) | `backend/` (PRs L6 a L11) | Sin cambios manuales de Luis al código. Carlos aprobó los PRs #7 a #12 y probó en PostgreSQL 16 el borrado en cascada y los permisos por rol |
| 2026-11-24 | Luis | Agente de Claude Code / Claude Sonnet 5.5 | Pantallas de reportar (bache y encharcamiento), duplicados, mis reportes y acciones de confirmación (69 pruebas nuevas) | `frontend/` (PRs L12 a L14) | Sin cambios manuales de Luis al código. Carlos aprobó los PRs #4 a #6 tras correr lint, pruebas y build y probar el flujo de ciudadano en el navegador |
| 2026-11-25 | Luis | Agente de Claude Code / Claude Sonnet 5.5 | Semilla de 500 reportes ficticios en 12 semanas con historial coherente | `db/seed.py`, `backend/tests/` (PR L5) | Sin cambios manuales de Luis al código. Luis pidió retomar la tarea; Carlos aprobó el PR #17 y corrió la semilla en PostgreSQL 16 |
| 2026-11-25 | Luis | Agente de Claude Code / Claude Sonnet 5.5 | Diagramas de arquitectura y entidad-relación a partir del código real | `docs/arquitectura.*`, `db/er.*` | Sin cambios manuales de Luis al código. Carlos aprobó el PR #14 tras contrastar los diagramas con el diseño técnico |
| 2026-11-25 | Luis | Agentes de Claude Code / Claude Opus 5.5 y Claude Sonnet 5.5 (revisores, solo lectura) | Revisar los 11 PRs de Carlos (#18 a #28) contra el contrato, los criterios de aceptación, la privacidad y la autorización; el orquestador publicó las revisiones con la cuenta de Luis | Comentarios en los PRs #18 a #28 (sin cambios de código) | Luis autorizó revisar y aprobar; se pidieron cambios en #28 |
| 2026-11-25 | Luis | Claude Code / Claude Sonnet 5.5 (orquestador) | Crear el proyecto en Neon, el servicio en Render y el proyecto en Vercel, configurar variables y CORS, y comprobar el despliegue | Servicios en Neon, Render y Vercel (sin cambios de código) | Luis autorizó crear los tres servicios y aprobó el acceso de Vercel a GitHub; las claves no se escribieron en ningún archivo |
| 2026-11-25 | Luis | Claude Code / Claude Sonnet 5.5 y agente con Claude Opus 5.5 | Redactar el borrador del reporte técnico y de la autoevaluación a partir del repositorio y darles el formato de un reporte previo del equipo (docx y PDF) | `docs/reporte/*`, `docs/REPORTE.docx`, `docs/REPORTE.pdf`, `docs/AUTOEVALUACION.md` (PR #31) | Luis entregó el modelo de formato y el número de control de Carlos; Carlos pidió cambios y después aprobó el PR |
| 2026-11-25 | Luis | Claude Code / Claude Sonnet 5.5 (orquestador) | Corregir las observaciones que quedaban de la revisión y comprobar antes de la etiqueta: secretos en el historial y arranque desde un clon limpio | `frontend/`, `docs/plan/CONTRATO_API.md` (PR #35) | Luis pidió las correcciones y autorizó las comprobaciones |
| 2026-11-25 | Luis | Claude Code / Claude Sonnet 5.5 (orquestador) y agente auditor con Claude Opus 5.5 | Registrar el backlog como issues, auditar los criterios de las historias indispensables antes de cerrarlas, corregir los botones de confirmar y desmentir y pedir a Carlos sus textos | Issues #36 a #80, `frontend/` (PR #81) | Luis pidió abrir los issues y cerrar solo lo completo |
| 2026-11-25 | Luis | Claude Code / Claude Sonnet 5.5 (orquestador) | Corregir los huecos que halló la auditoría: severidad y nivel del agua en la lista, filtro por sector en la consulta y rechazo de encharcamientos desde el detalle | `frontend/`, `backend/` (PRs #82 a #84) | Luis pidió corregir los tres |
| 2026-11-25 | Luis | Claude Code / Claude Sonnet 5.5 (orquestador) | Diagnosticar el error 404 del sitio publicado, desplegar y corregirlo, revisar el PR de Carlos, fusionar los PRs aprobados, agregar la insignia de CI y registrar el reparto 60/40 | Despliegue en Render, `backend/`, `.github/workflows/`, `README.md`, reporte (PRs #86 a #88) | Luis reportó el fallo con capturas y confirmó el porcentaje que propuso Carlos |
| 2026-11-26 | Luis | Claude Code / Claude Sonnet 5.5 (orquestador) | Verificar el estado antes de la entrega (PRs, revisiones, CI y despliegue), fusionar los PRs aprobados, tomar la captura de `/docs` y completar la parte de Luis en `AI_USAGE.md` | `docs/capturas/api-docs.png`, `AI_USAGE.md`, `docs/ai/bitacora-luis.md` | Luis pidió fusionar primero solo #86 y después #87 y #88, y decidió que la auditoría de accesibilidad la haga Carlos |
| 2026-11-25 | Carlos | Claude Code / Claude Sonnet 5.5 | Clonar el repositorio `liebres-urbanas`, analizar las tareas que le tocan a Carlos Limones Ayala y armar un proyecto local con las herramientas de la computadora, sin hacer commits ni PRs todavía | Ninguno en el repositorio (copia local de L1+L2+L3 fuera del repo, con base de datos en Docker, `.env` propio y dependencias instaladas) | Carlos eligió "copia aparte, sin commits" para no tocar `main` mientras los PRs de Luis siguen abiertos |
| 2026-11-25 | Carlos | Claude Code / Claude Sonnet 5.5 | Revisar y aprobar los 14 PRs de Luis; después trabajar las tareas de Carlos en PRs modulares, que revisa Luis y fusiona Carlos | Reviews en los PRs #1 a #14 (sin cambios de código); esta bitácora | Carlos fijó el flujo de trabajo. Las aprobaciones se publicaron después de leer el código, correr las pruebas de la punta de cada pila y probar el flujo de ciudadano en el navegador contra PostgreSQL real |
| 2026-11-25 | Carlos | Claude Code / Claude Sonnet 5.5 (orquestador) | Revisar y aprobar los PRs L4 (catálogo de colonias) y L5 (semilla), fusionar la bitácora, y repartir las historias de Carlos entre subagentes con instrucciones comunes (stack, privacidad, sin `git push` ni PRs, informe final) | Reviews en #16 y #17; ramas `feature/c3` a `c11` (ver filas siguientes); `docs/plan/CONTRATO_API.md` (secciones 8 a 14) | Carlos autorizó los subagentes y el flujo. El orquestador revisó cada diff, corrió pytest, ruff, lint, Vitest y build en cada rama, y abrió los PRs #18 a #26 |
| 2026-11-25 | Carlos | Subagente de Claude Code / Claude Opus 5.5 | C3 y C4: consulta pública `GET /api/reportes` con función única de filtrado y detalle `GET /api/reportes/{id}` con historial público, más sus pantallas | `backend/app/services/consulta.py`, `routers/consulta.py`, `core/deps.py`, `frontend/src/paginas/Consulta.tsx`, `DetalleReporte.tsx` (PRs #22 y #23) | Se revisó el campo nuevo `ultima_confirmacion` (única desviación del contrato). Queda pendiente decidir si el detalle ofrece "Confirmar" |
| 2026-11-25 | Carlos | Subagente de Claude Code / Claude Opus 5.5 | C6 y C7: bandeja de moderación, validar y rechazar con motivo, y avance de reparación con la máquina de estados | `backend/app/services/moderacion.py`, `routers/moderacion.py`, `frontend/src/paginas/Moderacion.tsx` y `moderacion/` (PRs #24 y #25) | Carlos decidió que bandeja, validar y rechazar queden solo para el moderador, como dice la tabla de endpoints |
| 2026-11-25 | Carlos | Subagente de Claude Code / Claude Opus 5.5 | C10: tablero de indicadores sobre la función única de consulta, con gráfica de barras en SVG propio | `backend/app/services/tablero.py`, `routers/tablero.py`, `frontend/src/paginas/Tablero.tsx`, `componentes/GraficaSemanal.tsx` (PR #26, apilado sobre #22) | La coincidencia entre tablero y lista la verifican las pruebas automáticas (en SQLite). Además, la comparación se hizo a mano con la aplicación sobre PostgreSQL 16 y la semilla de 500 reportes: los conteos por estado del tablero (75, 94, 56, 112 y 115) coincidieron con `GET /api/reportes` |
| 2026-11-25 | Carlos | Subagente de Claude Code / Claude Sonnet 5.5 | C5 (¿Cómo está mi zona?), C8 y C9 (administrar colonias, sectores y usuarios) y C11 (aviso de lluvia con Open-Meteo) | `backend/app/services/zona.py`, `catalogos.py`, `usuarios.py`, `clima.py` y sus routers; `frontend/src/paginas/Zona.tsx`, `AdminColonias.tsx`, `AdminUsuarios.tsx`, `componentes/AvisoLluvia.tsx` (PRs #19 a #21 y #18) | Se contrastó el formato real de Open-Meteo con un `curl`. Se corrigió el desborde horizontal de las tablas de administración a 360 px (`contain: layout`) |
| 2026-11-25 | Carlos | Claude Code / Claude Sonnet 5.5 (orquestador) | C12: instalar axe, Lighthouse y puppeteer-core fuera del repositorio, auditar las 12 vistas principales en 360 px y escritorio, tomar capturas y corregir lo que saliera | `docs/lighthouse/`, `docs/capturas/`, `docs/herramientas/auditar_accesibilidad.mjs`, `frontend/src/paginas/MisReportes.tsx` (PR #27) | Carlos autorizó la descarga de las herramientas. La primera pasada encontró dos problemas reales: desborde horizontal a 360 px en las tablas de administración (corregido en las ramas de #20 y #21) y un salto de encabezados en Mis reportes (corregido en #27). Los resultados finales (Lighthouse 100, axe 0) salieron después de corregirlos; la auditoría automática no sustituye la revisión manual |
| 2026-11-25 | Carlos | Claude Code / Claude Sonnet 5.5 (orquestador) | Fusionar en el orden de Luis los PRs aprobados (#18 a #27), resolviendo conflictos y corriendo todas las pruebas antes de cada fusión | `backend/app/main.py`, `backend/tests/test_seguridad.py`, `frontend/src/api/tipos.ts`, `docs/plan/CONTRATO_API.md` (conflictos mecánicos) | **Error de la IA:** fusionó #23 (apilado sobre la rama de C3) sin comprobar que su base seguía siendo esa rama, así que el detalle quedó en `feature/c3-consulta-reportes` y no en `main`. Se detectó al revisar `main` después de fusionar, se avisó y se corrigió con #30. Desde entonces cada fusión comprueba que la base sea `main`. Otro defecto del orquestador: su resolución automática de conflictos rompió llaves de `tipos.ts` y una lista de `test_seguridad.py`; lo detectaron las pruebas |
| 2026-11-26 | Carlos | Claude Code / Claude Sonnet 5.5 (orquestador) | Revisar y aprobar los PRs posteriores de Luis (#16, #17, #29, #31, #35 y #81 a #88): correr cada rama, leer el diff, comprobar cifras y publicar la revisión | Reviews en esos PRs (sin cambios de código) | Se corrigieron dos frases imprecisas de las propias reviews (#84 y #31) después de publicarlas; el despliegue se comprobó con peticiones de solo lectura; la IA no fusionó ningún PR de Luis |
| 2026-11-25 | Carlos | Subagentes de Claude Code / Claude Opus 5.5 (backend) y Claude Sonnet 5.5 (frontend); orquestador Claude Sonnet 5.5 (documentación) | Atender las observaciones de la revisión de Luis: carrera al moderar con bloqueo de fila, 422 en lugar de 500 con fechas extremas, tope de `pagina`, borrado de colonia en carrera, tiempo de espera de clima y `comentario_max`; foco del teclado, selector de rol, componente de confirmación compartido y detalles de moderación, zona y detalle; orden del contrato y notas de #27 | `backend/app/services/`, `frontend/src/paginas/`, `frontend/src/componentes/Confirmar.tsx`, `docs/plan/CONTRATO_API.md` (PRs #32, #33 y #34) | El orquestador revisó cada diff y corrió las suites; el bloqueo de fila se comprobó con dos sesiones concurrentes en PostgreSQL (SQLite no lo ejerce); Luis revisó y aprobó |
| 2026-11-26 | Carlos | Claude Code / Claude Sonnet 5.5 (orquestador) | Completar la parte de Carlos de `AI_USAGE.md`: herramienta, modelo y modo de uso (secciones 1 y 2) y sus filas de la bitácora consolidada (sección 4) | `AI_USAGE.md`, `docs/ai/bitacora-carlos.md` | Carlos lo pidió y revisó el resultado |
| 2026-11-26 | Carlos | Subagente de Claude Code / Claude Sonnet 5.5; orquestador Claude Sonnet 5.5 | Auditoría final de accesibilidad y responsividad: repetir axe y Lighthouse sobre `main` en 17 vistas locales (con login por rol) y en las 6 vistas públicas del sitio desplegado, sin iniciar sesión; después arreglar el hallazgo de foco del teclado en los formularios de moderación | `docs/lighthouse/README.md`, `docs/lighthouse/resultados.json`, `frontend/src/paginas/moderacion/`, `frontend/src/hooks/useFocoAlMontar.ts`, `frontend/src/utils/foco.ts` (PRs #92 y #93) | El orquestador revisó el informe y la consistencia de `resultados.json`; el subagente descartó una primera ronda por una contraseña de semilla equivocada; el arreglo de foco se comprobó con 4 pruebas nuevas (fallan sin el arreglo) y en Edge real contra PostgreSQL; el sitio desplegado se midió solo en lectura |
| 2026-11-26 | Carlos | Subagente de Claude Code / Claude Opus 5.5; orquestador Claude Sonnet 5.5 | Auditoría de seguridad de las historias C3 a C11 y los arreglos posteriores: matriz rol por endpoint en vivo (33 rutas), tokens manipulados, IDOR, carreras, privacidad, CORS, cabeceras, flujo de despliegue, secretos en el historial y dependencias | `docs/seguridad-backend.md` (PR #91) | El orquestador verificó contra el código tres hallazgos (S1, S7 y S12) antes de abrir el PR; el subagente trabajó solo en local y no tocó los sitios desplegados |
| 2026-11-26 | Carlos | Subagente de Claude Code / Claude Opus 5.5; orquestador Claude Sonnet 5.5 | Arreglar los hallazgos de bajo costo de la auditoría de seguridad: límite por hora con bloqueo de la fila del usuario (S1), reporte releído con bloqueo al editar o borrar (S3), ids enteros acotados al rango de PostgreSQL (S4), comodines en la búsqueda de colonias (S7) y limpieza de las pruebas y del diseño (S12) | `backend/app/services/`, `backend/app/schemas/comun.py`, `backend/tests/test_ids.py`, `docs/plan/` (PR #94) | El orquestador revisó el diff, corrió las suites y comprobó S1 y S3 en PostgreSQL real con peticiones concurrentes (10 altas y 5 rechazos de 15 simultáneas; el autor esperó y recibió 409), porque SQLite no ejerce el bloqueo |

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

**Reflexión crítica (Carlos).** Está en la sección 5 (Uso de IA) del reporte técnico: [`docs/reporte/REPORTE.md`](docs/reporte/REPORTE.md#5-uso-de-ia).

## Reglas de seguridad que seguimos

- Nunca se pegan en un asistente contraseñas, cadenas de conexión ni llaves de API reales. Las claves viven solo en los paneles de
  Render, Vercel y Neon.
- Se revisa que la IA no agregue dependencias inexistentes o abandonadas (riesgo A03 del OWASP Top 10:2025): una dependencia nueva
  se justifica antes de agregarla.
- Los datos de ejemplo son siempre ficticios.
