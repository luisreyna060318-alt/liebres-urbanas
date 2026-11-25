# Liebre Urbana — Plan de trabajo

Plataforma ciudadana de baches y encharcamientos para Ciudad Juárez (cliente ficticio: A.C. "Calles Seguras Juárez").
Proyecto final de Programación Web (AEB-1055, ITCJ, Dr. Roberto Contreras). Equipo de dos personas.

| | |
|---|---|
| Redactado | Martes 24 de noviembre de 2026 (versión 2: ajustada tras las respuestas de Luis) |
| Entrega y demo en vivo | **Jueves 26 de noviembre de 2026 a las 17:00** (versión `v1.0.0`) |
| Integrantes | Luis David Reyna Morisco (`luisreyna060318-alt`) y Carlos Limones Ayala (`LimonesCarlos`) |
| Repositorio de trabajo | `luisreyna060318-alt/liebres-urbanas` (aquí ocurre el flujo real: ramas, PRs y revisión cruzada) |
| Repositorio de entrega | `tecnm-itcj/aeb-1055-programacion-web-u5-final-group-3` (se sube todo al final; ver sección 6.5) |

Documentos hermanos de este plan:

- [BACKLOG.md](BACKLOG.md): las 34 historias de usuario, quién las hace, en qué prioridad y en qué PR.
- [CONTRATO_API.md](CONTRATO_API.md): formas exactas de las peticiones y respuestas; es lo que permite trabajar a la vez en backend y frontend.
- [DISENO_TECNICO.md](DISENO_TECNICO.md): arquitectura, modelo de datos, endpoints, reglas de negocio con sus valores y decisiones.
- [CHECKLIST_ENTREGA.md](CHECKLIST_ENTREGA.md): cada criterio de la rúbrica con su evidencia, su responsable y su fecha.

---

## 1. Lo primero que hay que saber

**Quedan unas 40 horas hasta la entrega**, y hay mucho que hacer: 20 historias indispensables, 9 requerimientos no funcionales, CI,
pruebas, Docker, despliegue, reporte de 20 páginas, `AI_USAGE.md` y autoevaluación. Entra, pero solo con este orden:

1. **Primero lo indispensable (P0)**, luego lo deseable (P1). Los cortes están definidos en la sección 2.
2. **Historias completas de punta a punta** (base de datos, API, pantalla y prueba), para que cada quien pueda explicar "del clic en
   React a la consulta en PostgreSQL" en la defensa.
3. **PRs pequeños y apilados**: esta noche Luis (con Claude como orquestador y agentes de apoyo) deja abiertos los PRs; Carlos los revisa
   mañana temprano, en orden, y se fusionan.
4. **Congelamiento del código el miércoles a las 23:00.** El jueves es para documentos, Lighthouse, la etiqueta `v1.0.0` y la entrega
   al repositorio de la organización. La etiqueta se crea a más tardar a las 15:00.

### Supuestos

- Luis trabaja desde esta noche; Carlos desde las 08:00 del miércoles (tiene Docker y Node).
- Luis lleva más carga hoy para adelantar lo más posible. El reparto "50/50" se verifica el miércoles a las 20:00 y se compensa con
  las historias deseables y los documentos (sección 3).
- Se programa con asistentes de IA y se declara todo en `AI_USAGE.md`, incluidos los agentes de apoyo y sus modelos.
- No se piden cambios al cliente ni ampliación de plazo.
- Se reutiliza infraestructura del proyecto previo `extra-liebres` (Docker, CI, despliegue) después de comprobar que cubre lo de este
  proyecto o de adaptarla. Esa parte queda a cargo de Luis.

---

## 2. Alcance

| Nivel | Qué incluye | Cuándo debe estar listo |
|---|---|---|
| **P0 — se entrega sí o sí** | Las **20 historias indispensables**, los 9 requerimientos no funcionales y los requisitos de la materia (≥ 12 endpoints, ≥ 8 pruebas `pytest`, CI, Docker Compose, despliegue, documentos) | Miércoles 25, 20:00 |
| **P1 — si P0 está desplegado** | 8 historias deseables baratas que además dan puntos extra: **HU-04.5** mapa, **HU-07.3** exportar CSV/XML, **HU-01.4** colonias de interés, **HU-03.4** puntos recurrentes, **HU-07.2** resumen por colonia, **HU-06.3** catálogos de tipos y motivos, **HU-08.2** avisos sobre mis reportes, **HU-08.3** encharcamientos sin recargar | Miércoles 25, 23:00 |
| **P2 — trabajo futuro** | **HU-02.4** fotos, **HU-04.6** trayecto, **HU-05.3** fusionar duplicados, **HU-05.4** cuadrillas, **HU-05.5** enlace municipal, **HU-08.4** PWA | Solo si sobra tiempo real |

Puntos extra de la materia (hasta +5) que caen dentro de P1: mapa y geolocalización (HU-04.5 y Nominatim), XML (HU-07.3) y pruebas
del frontend con Vitest. No se intenta Kubernetes ni WebSockets.

**Orden de recorte** si el tiempo se acaba: P2 → P1 en orden inverso → pulido visual. Nunca se recortan las 20 indispensables ni los
requisitos de entrada (Compose, `AI_USAGE.md`, `v1.0.0`, autoevaluación).

---

## 3. Reparto del trabajo

### 3.1 Áreas transversales (lo que cada quien debe poder defender solo)

| | Luis | Carlos |
|---|---|---|
| Base de datos | Modelo ER, modelos SQLAlchemy, migración Alembic, restricciones y triggers, semilla (colonias reales + 500 reportes) | Revisión de PRs de la base de datos; consultas del tablero |
| Backend | Esqueleto FastAPI, errores uniformes, **autenticación y roles**, geocodificación (Nominatim) | Servicio de clima (Open-Meteo), consulta común de reportes con filtros, moderación, administración |
| Frontend | **Esqueleto React**, estilos, componentes, rutas protegidas, formularios de cuenta y de reporte | Consulta pública, zona, detalle, moderación, administración, tablero; **accesibilidad y Lighthouse** |
| DevOps | **Dockerfiles, Compose, CI, despliegue** (Neon + Render + Vercel). Se reutiliza y adapta lo de `extra-liebres` | Revisión de CI; plan B local |
| Calidad | Pruebas de sus historias y de seguridad | Pruebas de sus historias, **Vitest** |
| Documentos | Portada, Planeación, Ejecución (backend, BD, seguridad, contenedores, despliegue), `AI_USAGE.md` | Fundamentación, Ejecución (frontend), Evaluación (pruebas, Lighthouse), Contribución, Autoevaluación |

### 3.2 Historias indispensables: 10 y 10

| Luis — "Reportar y mantener vivo el reporte" | Carlos — "Consultar, validar y gestionar" |
|---|---|
| HU-01.1 Crear una cuenta | HU-04.1 Consultar reportes activos sin cuenta |
| HU-01.2 Iniciar y cerrar sesión | HU-04.2 Buscar y filtrar reportes |
| HU-01.3 Hacer solo lo que mi rol permite | HU-04.3 ¿Cómo está mi zona? |
| HU-02.1 Reportar un bache | HU-04.4 Ver el detalle y la historia de un reporte |
| HU-02.2 Describir el daño según su tipo | HU-05.1 Validar o rechazar reportes nuevos |
| HU-02.3 Evitar reportes duplicados | HU-05.2 Registrar el avance de una reparación |
| HU-02.5 Consultar y corregir mis reportes | HU-06.1 Administrar colonias y sectores |
| HU-03.1 Reportar un encharcamiento | HU-06.2 Administrar usuarios y roles |
| HU-03.2 Vigencia automática del encharcamiento | HU-07.1 Tablero de indicadores |
| HU-03.3 Confirmar o desmentir un encharcamiento | HU-08.1 Aviso de lluvia |

### 3.3 Historias deseables (P1)

Como Luis carga con la infraestructura y el frontend base, Carlos se queda con la mayor parte de lo deseable. La regla es: **las
historias P0 de cada quien son suyas**; las P1 se reparten el miércoles a las 20:00 según la carga real.

| Luis | Carlos |
|---|---|
| HU-01.4 Colonias de interés (relación N:M explícita) | HU-04.5 Mapa de reportes (Leaflet) |
| HU-08.2 Avisos sobre mis reportes | HU-07.2 Resumen público por colonia |
| | HU-07.3 Exportar CSV y XML |
| | HU-08.3 Encharcamientos nuevos sin recargar |
| | HU-03.4 Puntos recurrentes |
| | HU-06.3 Tipos de daño y motivos de rechazo |

### 3.4 Quién defiende qué en la demo

| Tramo de la demo (8 min) | Quién | Lo que se muestra |
|---|---|---|
| Problema y usuarios (0:30) | Luis | Una frase del problema y los 4 roles |
| Recorrido de ciudadano (3:00) | Luis | Registro, login, reportar bache (con duplicado a 30 m), reportar encharcamiento, Mis reportes, filtro y búsqueda |
| Recorrido de moderador y coordinador (2:00) | Carlos | Bandeja, validar y rechazar, avance de reparación, tablero |
| Prueba de que el servidor bloquea (0:45) | Carlos | Un ciudadano intenta una función de moderador en `/docs`: responde 403 |
| Servicio externo (0:30) | Luis (Nominatim) y Carlos (clima) | Dirección que se convierte en coordenadas y aviso de lluvia |
| Vista técnica (1:15) | Luis | `/docs`, CI en verde, paneles de Render, Vercel y Neon |

El docente puede preguntarle a cualquiera sobre cualquier parte. Por eso el jueves a las 12:30 hay un **ensayo cruzado** de 30 minutos:
cada quien explica el flujo completo de una historia de la otra persona.

---

## 4. Cronograma

Horas de ciudad de Juárez. Las puertas (G) son puntos de control: si una no se cumple, se aplica el orden de recorte.

### Martes 24 (esta noche) — Luis con Claude y agentes de apoyo

| Cuándo | Qué |
|---|---|
| **G0** | Repositorio personal creado, Carlos invitado, primer commit en `main`, Docker Desktop verificado |
| Oleada 1 (en paralelo) | **L1** API, modelos, migración y autenticación · **L2** React base y pantallas de cuenta · **L3** Docker, Compose, CI y archivos de despliegue · **L4** catálogo oficial de colonias |
| Oleada 2 | **L5** semilla de 500 reportes · **L6 a L11** historias de Luis en el backend · **L12 a L14** pantallas de esas historias |
| Al cerrar la noche | Todos los PRs abiertos y apilados, con CI corriendo, descripción y orden de revisión; la mayor parte de P0 de Luis hecha |

### Miércoles 25

| Hora | Qué | Luis | Carlos |
|---|---|---|---|
| 08:00 | Arranque de 15 min: leer el orden de revisión y confirmar horarios | ambos | ambos |
| 08:15–10:30 | **G1**: Carlos revisa y aprueba los PRs en orden (de abajo hacia arriba); Luis los fusiona conforme se aprueban | Resuelve comentarios y fusiona | **Revisa** |
| 10:30–13:00 | Luis: despliegue de humo (Neon + Render + Vercel). Carlos arranca con lo suyo desde `main` | **L15** despliegue | C3 y C4 (consulta y detalle) |
| 13:00–14:00 | **G2**: URL pública funcionando con registro, login y lista de reportes | ambos | ambos |
| 14:00–20:00 | Historias P0 de Carlos y cierre de P0 de Luis; Luis revisa los PRs de Carlos conforme salen | Revisa, pruebas, seguridad, huecos | C5 a C11 |
| 20:00 | **G3**: las 20 historias P0 fusionadas y desplegadas. Se reparte P1 según la carga real | ambos | ambos |
| 20:00–23:00 | P1, pruebas finales, borrador del reporte | P1 | P1 |
| **23:00** | **G4: congelamiento de código.** Solo se corrigen fallas | ambos | ambos |

### Jueves 26 (entrega a las 17:00)

| Hora | Qué | Quién |
|---|---|---|
| 08:00–11:00 | Lighthouse y capturas en móvil y escritorio; reporte técnico (cada quien sus secciones); `AI_USAGE.md` final | Carlos (Lighthouse y capturas), ambos (reporte) |
| 11:00–12:30 | Autoevaluación con evidencia enlazada; README con URL, usuarios de prueba e insignia | Ambos |
| 12:30–13:00 | Ensayo cruzado de defensa | Ambos |
| 13:00–14:30 | Revisión final de la checklist, prueba del plan B (`docker compose up` con cronómetro), búsqueda de secretos | Luis y Carlos |
| **15:00** | **G5**: `main` con CI en verde, etiqueta **`v1.0.0`**; subir todo al repositorio de la organización (sección 6.5) | Luis crea la etiqueta; Carlos la verifica |
| 15:30–16:30 | Ensayo de la demo con cronómetro; abrir el frontend y llamar `/api/health` para despertar Render y Neon | Ambos |
| **17:00** | **Entrega y demo** | Ambos |

---

## 5. Tareas por persona

Las estimaciones suponen asistencia de IA e incluyen pruebas y PR, pero no la espera de la revisión. Cada fila es un PR en el
repositorio de trabajo; las ramas se llaman `feature/<id>-<tema>`.

### 5.1 Luis (esta noche, con Claude y agentes de apoyo)

| PR | Base | Contenido | Historias |
|---|---|---|---|
| L0 | commit directo a `main` | Plan, contrato, README base, `.gitignore`, `AI_USAGE.md`, `CODEOWNERS`, plantilla de PR | — |
| L1 | `main` | Esqueleto FastAPI en capas, configuración, errores uniformes, modelos de todas las tablas, migración Alembic (con triggers), catálogos y cuentas de demo, registro, login, refresh, `require_role`, lecturas de catálogos, `/api/reglas`, `/api/health`, pruebas | HU-01.1 y HU-01.2 (API) |
| L2 | `main` | Vite + React + TypeScript, rutas, diseño semántico, CSS responsivo desde 360 px, componentes (Campo, Boton, Alerta, Cargando, Vacio, Paginacion), contexto de sesión, rutas protegidas por rol, cliente de la API, hook `useApi`, pantallas de registro, login y cierre de sesión, sesión inactiva | HU-01.1, HU-01.2, HU-01.3 (UI), RNF-01, RNF-02, RNF-08 |
| L3 | `main` | Dockerfile de backend y frontend, `docker-compose.yml`, `.env.example`, `ruff.toml`, GitHub Actions (ruff, pytest, lint y build del frontend), `render.yaml`, `vercel.json`, guía de despliegue, `CLAUDE.md` | RNF-04 |
| L4 | L1 | Catálogo oficial de asentamientos de Juárez con su fuente (`db/datos/`) | RNF-09 |
| L5 | L4 | Semilla idempotente: 20+ colonias reales, 500 reportes ficticios en 12 semanas con historial coherente, una cuenta por rol | RNF-09 |
| L6 | L5 | Servicio de Nominatim (caché, tolerancia a fallas), validación de municipio, folio, alta del bache, hora del servidor, límite de 10 por hora | HU-02.1 |
| L7 | L6 | Tipos de daño: validación por tipo, severidad automática | HU-02.2 |
| L8 | L7 | Reportes cercanos (30 m), confirmar sin folio nuevo, una confirmación por persona, reportar de todos modos | HU-02.3 |
| L9 | L8 | Mis reportes: paginación, editar y eliminar solo en Recibido | HU-02.5 |
| L10 | L9 | Encharcamientos: alta, vigencia de 6 h, confirmar y desmentir, 3 desmentidos | HU-03.1, HU-03.2, HU-03.3 |
| L11 | L10 | Pruebas de la matriz rol × endpoint y de privacidad; revisión A01 y A02 | HU-01.3, RNF-05, RNF-07 |
| L12 | L2 | Pantalla "Reportar bache": ubicación, formulario dinámico, duplicados | HU-02.1, HU-02.2, HU-02.3 (UI) |
| L13 | L12 | Pantalla "Mis reportes" | HU-02.5 (UI) |
| L14 | L13 | Pantalla "Reportar encharcamiento" y confirmar o desmentir | HU-03.1 a HU-03.3 (UI) |

Mañana, Luis: despliegue (L15), revisión de los PRs de Carlos, pruebas, huecos de seguridad, documentos y P1 asignadas.

### 5.2 Carlos (desde las 08:00 del miércoles)

Primero, revisar los PRs de Luis (unas 2 horas), después:

| PR | Contenido | Historias | Est. |
|---|---|---|---|
| C3 | Lista pública de reportes activos, filtros, búsqueda por calle o folio, paginación de 20 en 20 | HU-04.1, HU-04.2 | 2 h |
| C4 | Detalle e historial, longevidad en días | HU-04.4 | 1 h |
| C5 | ¿Cómo está mi zona? (1 km, por distancia) | HU-04.3 | 1.25 h |
| C6 | Bandeja de moderación, validar, rechazar con motivo | HU-05.1 | 1.5 h |
| C7 | Avance de reparación, máquina de estados RN-05, historial inalterable | HU-05.2 | 1.5 h |
| C8 | Catálogo de colonias y sectores | HU-06.1 | 1 h |
| C9 | Usuarios y roles | HU-06.2 | 1.25 h |
| C10 | Tablero de indicadores | HU-07.1 | 2 h |
| C11 | Aviso de lluvia con Open-Meteo | HU-08.1 | 1 h |
| C12 | Vitest, accesibilidad (axe y Lighthouse ≥ 90), capturas | RNF-02 | 1 h |
| P1 | Un PR por historia: HU-04.5, 07.2, 07.3, 08.3, 03.4, 06.3 | | 0.75 h c/u |

El código de Luis ya trae el esqueleto, los componentes y los endpoints de catálogos, así que Carlos arranca sobre una base funcional.

### 5.3 Dependencias entre los PRs

| Quien espera | Necesita | Se resuelve así |
|---|---|---|
| Carlos (todo) | Base de L1, L2 y L3 en `main` | Se revisan y fusionan primero (08:15 a 10:30) |
| Carlos (C5) | `GET /api/geo/buscar` de L6 | L6 es el primero de la cadena de reportes |
| Carlos (C7) | `registrar_cambio_estado()` | Vive en L1 |
| Ambos | Migraciones de Alembic | **Solo Luis crea migraciones**; Carlos las pide por mensaje (nunca hay dos "heads") |

---

## 6. Flujo de trabajo en Git

### 6.1 Reglas del equipo

1. `main` solo recibe cambios por pull request, **salvo el primer commit**.
2. Los PRs de Luis los revisa y aprueba Carlos; los de Carlos los revisan y aprueban Luis. **Nadie fusiona su propio PR sin la
   aprobación de la otra persona.**
3. Un PR es una historia (o dos muy pequeñas). Meta: menos de 400 líneas.
4. CI en verde antes de fusionar.
5. **Fusionar con "merge commit"** (no "squash") para conservar los commits individuales (evidencia de contribución).
6. Cada quien hace commits con **su propia cuenta**.
7. Conventional Commits en español: `feat(reportes): detecta duplicados a 30 m`, `fix:`, `docs:`, `test:`, `chore:`.
8. Los commits con código generado por IA terminan con `Co-Authored-By:` (con el modelo real que lo generó) o `Assisted-by:`.
9. Archivos compartidos (`models/`, migraciones, rutas del frontend, cliente de la API): solo en PRs pequeños y avisando.
10. **Bitácora de IA separada**: `docs/ai/bitacora-luis.md` y `docs/ai/bitacora-carlos.md`; se consolidan en `AI_USAGE.md` al final.

### 6.2 PRs apilados (cómo se revisan mañana)

Esta noche los PRs dependen unos de otros. Cada PR abre contra el PR anterior (su rama base es la rama del anterior) y lo dice en la
descripción. Para Carlos:

1. Revisa **de abajo hacia arriba** (L1, L2, L3, luego L4, L5…); el orden está en el PR de cada uno y en el comentario de Luis.
2. Cuando un PR se aprueba, Luis lo fusiona con "merge commit". GitHub cambia solo la base del PR de arriba a `main`.
3. Si una revisión pide cambios, se corrigen en la rama de ese PR y los PRs de arriba se actualizan con `git rebase` o `git merge`.

### 6.3 Reglas de Luis para Claude y los agentes

| Acción | Regla |
|---|---|
| Commits y PRs en `liebres-urbanas` | Autorizados por Luis para esta noche. Cada commit se revisa antes (sin secretos, datos reales ni documentos del docente) |
| Fusionar un PR | Solo después de que Carlos lo apruebe |
| Subir al repositorio de la organización | Solo al final y con orden expresa de Luis |
| Neon, Render y Vercel (crear, variables, desplegar) | Con aviso previo a Luis; las claves **nunca** se imprimen en el chat |
| Descargas | Solo el catálogo de colonias, autorizado por Luis |

### 6.4 Revisión de un PR (para quien revisa, 10 minutos)

1. ¿Cumple los criterios de aceptación de la historia? Correr la rama y probarlo.
2. ¿Hay prueba de la regla de negocio principal?
3. ¿Hay autorización por rol en el servidor, no solo botones ocultos?
4. ¿Algún secreto, dato personal en una respuesta pública o dependencia nueva sin justificar?
5. ¿Se entiende el código? Quien revisa debe poder explicarlo en la defensa.

### 6.5 Llevar todo al repositorio de la organización

El repositorio personal es el lugar de trabajo; la entrega es el de la organización. El jueves, después de G5 (CI en verde y etiqueta
`v1.0.0`), Luis empuja a la organización la rama `main` completa con su historial y la etiqueta:
`git push org main` y `git push org v1.0.0`, de modo que los commits conserven a su autor. Los PRs y las revisiones quedan en el
repositorio personal; su enlace se pone en el reporte como evidencia del flujo. `main` de la organización no tiene protección (solo el
docente es administrador); no se pide cambiarlo.

---

## 7. Definición de "terminado" para una historia

- [ ] Sus criterios de aceptación (CA) se observan en el producto funcionando, desde la interfaz.
- [ ] Hay al menos una prueba automatizada de su regla principal.
- [ ] La regla del servidor se cumple aunque alguien llame la API sin usar la pantalla.
- [ ] Estados de **carga, error y vacío** en la pantalla.
- [ ] Funciona desde 360 px y con teclado; texto en español de México.
- [ ] No expone datos personales (RN-04).
- [ ] PR revisado por la otra persona, CI en verde, fusionado.
- [ ] El PR menciona el ID (`HU-02.3`) y la bitácora de IA tiene su fila.

---

## 8. Despliegue (Vercel + Render + Neon) y plan B

```
Navegador ──> Vercel (React, estático) ──> Render (FastAPI en Docker) ──> Neon (PostgreSQL)
                                                  ├──> Nominatim (direcciones)
                                                  └──> Open-Meteo (pronóstico)
```

Render y Vercel están conectados a la cuenta personal de Luis, y el repositorio de trabajo es suyo, así que pueden leerlo. Se parte de
`render.yaml`, `vercel.json` y `entrypoint.sh` de `extra-liebres`, revisados y adaptados.

| Pieza | Cómo | Notas |
|---|---|---|
| Neon | Un proyecto `liebre-urbana`; conexión **directa** (sin `-pooler`) | La cadena de conexión nunca se pega en chats ni en Git |
| Render | Servicio web Docker desde `backend/Dockerfile`; al arrancar corre `alembic upgrade head` y la semilla si la base está vacía | Variables: `DATABASE_URL`, `SECRET_KEY` (generada), `CORS_ORIGINS`, `ENTORNO=produccion` |
| Vercel | Proyecto con raíz `frontend/`, variable `VITE_API_URL` | Reescritura a `index.html` para las rutas de React |
| CORS | Solo el dominio de Vercel | Primer lugar donde mirar si algo falla en producción |
| Humo del miércoles | Registro + login + lista de reportes en la URL pública (**G2**, 13:00) | Detecta problemas de CORS y permisos con tiempo |

**Plan B (RNF-04):** `docker compose up` levanta frontend, backend y PostgreSQL en menos de 3 minutos. Para lograrlo, antes de la demo las
imágenes ya están construidas (`docker compose build`) y Docker Desktop está abierto. Sin internet, el pronóstico muestra "Pronóstico no
disponible" y las direcciones se capturan a mano; el resto funciona.

---

## 9. Riesgos

| # | Riesgo | Qué hacemos |
|---|---|---|
| R1 | Mucho trabajo para 40 horas | P0/P1/P2, puertas G0 a G5, recorte ordenado, PRs chicos |
| R2 | Carlos tiene que revisar ~15 PRs el miércoles temprano | PRs pequeños con descripción y pasos de prueba; orden de revisión explícito; CI ya corriendo; Luis fusiona al instante |
| R3 | PRs apilados que se desordenan | Cada PR dice de cuál depende; merge commit; rebase de los de arriba |
| R4 | Arranque en frío de Render (30 a 60 s) | Estados de carga claros; calentar servicios 10 min antes |
| R5 | Nominatim con límites o caído | Un pedido por segundo, caché, mensaje claro y captura manual; simulado en pruebas |
| R6 | Catálogo oficial de colonias (RNF-09) | Fuente oficial citada (Correos de México o INEGI); si no se logra descargar, se documenta y no se inventan datos |
| R7 | Dos "heads" de Alembic | Solo Luis crea migraciones |
| R8 | Hora local y horario de verano de Juárez (RN-02) | Guardar en UTC, mostrar con `America/Ciudad_Juarez`, pruebas con fechas cercanas al cambio |
| R9 | Un integrante no sabe explicar el código (sobre todo lo generado esta noche) | Código simple; ensayo cruzado; Carlos revisa todo lo de Luis; marcar lo generado por IA |
| R10 | Secretos en el historial (el repositorio personal es **público**) | `.env` ignorado, revisión antes de cada commit, claves solo en paneles; nunca una cadena de conexión en un commit, issue o PR |
| R11 | La contribución de Luis supera mucho a la de Carlos | Se reparte P1 y documentos el miércoles; el docente puede ajustar con la tabla de contribución. Se documenta tal como fue |
| R12 | Datos de demostración parecen reales | Todo ficticio salvo el catálogo oficial de colonias |

---

## 10. Pendientes de decisión

- Activar la protección de `main` en el repositorio personal (exigir 1 aprobación): Luis es administrador; en un repositorio privado
  podría no estar disponible en el plan gratuito. Hoy el repositorio es público, así que sí se puede. **Se hace solo si Luis lo pide.**
