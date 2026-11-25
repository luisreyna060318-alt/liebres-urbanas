<div class="portada">

<p class="inst">Tecnológico Nacional de México<br>Instituto Tecnológico de Ciudad Juárez</p>

<p class="materia">Programación Web (AEB-1055)<br>Proyecto final · agosto a diciembre de 2026</p>

<h1 class="titulo">Liebre Urbana</h1>

<p class="subtitulo">Plataforma ciudadana de baches y encharcamientos de Ciudad Juárez<br>Reporte técnico</p>

<table class="integrantes">
<thead><tr><th>Integrante</th><th>Número de control</th><th>Rol en el equipo</th></tr></thead>
<tbody>
<tr><td>Luis David Reyna Morisco</td><td>22111443</td><td>Base de datos, backend (cuentas, roles, geocodificación y reportes del ciudadano), frontend base, Docker, CI y despliegue</td></tr>
<tr><td>Carlos Limones Ayala</td><td>[NÚMERO DE CONTROL DE CARLOS]</td><td>Consulta pública, zona, detalle, moderación, administración, tablero y aviso de lluvia (de punta a punta); accesibilidad y pruebas del frontend</td></tr>
</tbody>
</table>

<table class="enlaces">
<tr><th>Repositorio</th><td>https://github.com/luisreyna060318-alt/liebres-urbanas</td></tr>
<tr><th>Aplicación desplegada</th><td>https://liebre-urbana.vercel.app</td></tr>
<tr><th>API y documentación</th><td>https://liebre-urbana-api.onrender.com/docs</td></tr>
<tr><th>Docente</th><td>Dr. Roberto Contreras</td></tr>
<tr><th>Fecha de entrega</th><td>26 de noviembre de 2026 (versión <code>v1.0.0</code>)</td></tr>
</table>

<p class="nota-portada">El cliente (A.C. "Calles Seguras Juárez") es ficticio y se creó con fines académicos. Los datos de demostración son ficticios, salvo el catálogo de colonias, que es real y cita su fuente.</p>

</div>

<div class="aviso-borrador" markdown="1">

**Cómo leer este borrador.** Lo que todavía no está fusionado en `main` aparece como **[PENDIENTE: …]** y lo que solo puede escribir
una persona del equipo como **[BORRADOR PARA REVISIÓN DE …]**. Las cifras de commits, PRs y pruebas se tomaron del repositorio de
trabajo el 25 de noviembre de 2026 por la tarde (hora de Ciudad Juárez) y se actualizan antes de la etiqueta `v1.0.0`.

</div>

## 1. Fundamentación

### 1.1 Problema

En Ciudad Juárez los vecinos reportan baches por redes sociales y aplicaciones de mensajería. Esos reportes se pierden entre
otras publicaciones, se repiten y casi nunca se sabe si alguien los atendió. Con las lluvias pasa algo parecido: algunas calles
se inundan y los conductores se enteran hasta que llegan al charco. La asociación civil "Calles Seguras Juárez" (cliente ficticio
de la materia) nos pidió una plataforma para **reportar, consultar por zona y dar seguimiento** a baches y encharcamientos, con
cifras que la mesa directiva pueda presentar a la autoridad.

### 1.2 Usuarios

| Rol | Qué hace en la plataforma |
|---|---|
| Visitante (sin cuenta) | Consulta los reportes activos, busca por calle o folio, revisa "¿Cómo está mi zona?" y ve el aviso de lluvia |
| Ciudadano | Reporta baches y encharcamientos, confirma o desmiente reportes de otras personas y corrige los suyos mientras están en Recibido |
| Moderador (voluntario) | Valida o rechaza los reportes nuevos y registra el avance de una reparación |
| Coordinador (mesa directiva) | Administra colonias, sectores y usuarios, avanza reparaciones y consulta el tablero de indicadores |

### 1.3 Contexto

Es un proyecto escolar de dos personas con unas 40 horas reales de trabajo (del martes 24 por la noche al jueves 26 a las 17:00).
La materia exige React, FastAPI y PostgreSQL, al menos un servicio externo consumido desde el backend, Docker Compose, despliegue
público y un flujo de trabajo con PRs revisados. Por el tamaño del equipo, el alcance se dividió en niveles (P0, P1 y P2) desde el
primer día.

### 1.4 Productos similares

Existen plataformas de reporte ciudadano de problemas urbanos, como FixMyStreet (mySociety, s. f.), donde el vecino marca un
problema en el mapa y la plataforma lo envía a la autoridad responsable, y aplicaciones de navegación con reportes de la comunidad,
como Waze (s. f.), que avisan de incidentes en el camino. Los municipios también suelen tener sus propios canales (teléfono, redes
sociales o formularios). No hicimos un análisis a fondo de esos productos ni de los canales del municipio de Juárez; los usamos
como referencia de ideas. Lo que Liebre Urbana agrega para el caso de la asociación es: detección de duplicados por distancia
(30 m para baches, 50 m para encharcamientos), vigencia automática de los encharcamientos (6 h que se renuevan con cada
confirmación), moderación por voluntarios con un historial que no se puede borrar y un aviso de lluvia que lleva a la consulta por
zona.

### 1.5 Alcance

| Nivel | Qué incluye | Estado al redactar |
|---|---|---|
| P0 (se entrega sí o sí) | 20 historias indispensables, 9 requerimientos no funcionales y los requisitos de la materia | 17 historias en `main`; 3 en PRs en revisión (sección 2.1) |
| P1 (si P0 está desplegado) | 8 historias deseables (mapa, exportar CSV/XML, colonias de interés, puntos recurrentes, resumen por colonia, catálogos, avisos, encharcamientos sin recargar) | [PENDIENTE: ninguna iniciada al redactar; actualizar] |
| P2 (trabajo futuro) | 6 historias (fotos, trayecto, fusionar duplicados, cuadrillas, enlace municipal, PWA) | Fuera del alcance (sección 4.5) |

## 2. Planeación

### 2.1 Historias de usuario

El backlog completo está en [`docs/plan/BACKLOG.md`](https://github.com/luisreyna060318-alt/liebres-urbanas/blob/main/docs/plan/BACKLOG.md):
**34 historias** agrupadas en 8 épicas, cada una con su ID (HU-xx.x), prioridad del cliente (I = indispensable, D = deseable),
nivel (P0, P1, P2), responsable, PR y la forma de cumplir sus criterios de aceptación (CA1, CA2…). La tabla resume el estado.

<div class="tabla-chica" markdown="1">

| ID | Historia | Pri. | Nivel | Dueño | Estado (PR) |
|---|---|---|---|---|---|
| HU-01.1 | Crear una cuenta | I | P0 | Luis | En `main` (#1, #2) |
| HU-01.2 | Iniciar y cerrar sesión | I | P0 | Luis | En `main` (#1, #2) |
| HU-01.3 | Hacer solo lo que mi rol permite | I | P0 | Luis | En `main` (#2, #12) |
| HU-01.4 | Elegir mis colonias de interés | D | P1 | Luis | No iniciada |
| HU-02.1 | Reportar un bache | I | P0 | Luis | En `main` (#7, #4) |
| HU-02.2 | Describir el daño según su tipo | I | P0 | Luis | En `main` (#8, #4) |
| HU-02.3 | Evitar reportes duplicados | I | P0 | Luis | En `main` (#9, #4) |
| HU-02.4 | Adjuntar fotografías | D | P2 | — | Trabajo futuro |
| HU-02.5 | Consultar y corregir mis reportes | I | P0 | Luis | En `main` (#10, #5) |
| HU-03.1 | Reportar un encharcamiento | I | P0 | Luis | En `main` (#11, #6) |
| HU-03.2 | Vigencia automática | I | P0 | Luis | En `main` (#11) |
| HU-03.3 | Confirmar o desmentir | I | P0 | Luis | En `main` (#11, #6) |
| HU-03.4 | Puntos recurrentes | D | P1 | Carlos | No iniciada |
| HU-04.1 | Consultar reportes activos sin cuenta | I | P0 | Carlos | En `main` (#22) |
| HU-04.2 | Buscar y filtrar reportes | I | P0 | Carlos | En `main` (#22) |
| HU-04.3 | ¿Cómo está mi zona? | I | P0 | Carlos | En `main` (#19) |
| HU-04.4 | Detalle e historia de un reporte | I | P0 | Carlos | [PENDIENTE: aprobado en #23; llega a `main` con #30] |
| HU-04.5 | Ver los reportes en un mapa | D | P1 | Carlos | No iniciada |
| HU-04.6 | Revisar mi trayecto | D | P2 | — | Trabajo futuro |
| HU-05.1 | Validar o rechazar reportes nuevos | I | P0 | Carlos | En `main` (#24) |
| HU-05.2 | Registrar el avance de una reparación | I | P0 | Carlos | En `main` (#25) |
| HU-05.3 | Fusionar reportes duplicados | D | P2 | — | Trabajo futuro |
| HU-05.4 | Asignar baches a una cuadrilla | D | P2 | — | Trabajo futuro |
| HU-05.5 | Actualizar baches desde la autoridad | D | P2 | — | Trabajo futuro |
| HU-06.1 | Administrar colonias y sectores | I | P0 | Carlos | En `main` (#20) |
| HU-06.2 | Administrar usuarios y roles | I | P0 | Carlos | [PENDIENTE: en revisión, #21] |
| HU-06.3 | Tipos de daño y motivos de rechazo | D | P1 | Carlos | No iniciada |
| HU-07.1 | Tablero de indicadores | I | P0 | Carlos | [PENDIENTE: en revisión, #26] |
| HU-07.2 | Resumen público por colonia | D | P1 | Carlos | No iniciada |
| HU-07.3 | Exportar para la autoridad (CSV y XML) | D | P1 | Carlos | No iniciada |
| HU-08.1 | Aviso de lluvia | I | P0 | Carlos | En `main` (#18) |
| HU-08.2 | Avisos sobre mis reportes | D | P1 | Luis | No iniciada |
| HU-08.3 | Encharcamientos nuevos sin recargar | D | P1 | Carlos | No iniciada |
| HU-08.4 | Instalar en el celular (PWA) | D | P2 | — | Trabajo futuro |

</div>

Además hay 9 requerimientos no funcionales (RNF-01 a RNF-09): pantallas desde 360 px, accesibilidad WCAG 2.2 AA, URL pública,
levantar todo en menos de 3 minutos, contraseñas invisibles, consulta en menos de 3 s con 500 reportes, pruebas automatizadas,
español de México y datos de demostración.

### 2.2 Tablero

El plan preveía un tablero en GitHub Projects con columnas Pendiente, En curso, En revisión y Hecho, alimentado con un issue por
historia. **No se creó**: al redactar, el repositorio no tiene issues ni un proyecto de GitHub Projects para Liebre Urbana. En la
práctica el seguimiento se hizo con `BACKLOG.md` (columna PR de cada historia), la descripción de cada PR (historia, cómo probarlo
y lista de verificación) y la lista de PRs abiertos y fusionados, que funcionó como tablero real del avance.
[PENDIENTE: si el equipo crea el tablero antes de la entrega, agregar el enlace y aclarar desde cuándo existe.]

### 2.3 Cronograma real

El plan ([`PLAN_DE_TRABAJO.md`](https://github.com/luisreyna060318-alt/liebres-urbanas/blob/main/docs/plan/PLAN_DE_TRABAJO.md),
sección 4) tenía puntos de control G0 a G5. Lo que pasó en realidad, según las fechas de los commits y de los PRs (hora de Ciudad
Juárez, UTC−7):

| Cuándo | Qué pasó | Plan |
|---|---|---|
| Mar 24, 23:25 | Primer commit en `main`: plan, contrato de la API y archivos base | G0 |
| Mar 24, 23:25 a Mié 25, 00:59 | Luis, con el orquestador y agentes de apoyo, hace 58 commits en las ramas L1 a L14 | Oleadas 1 y 2 |
| Mar 24, 23:51 a Mié 25, 00:26 | Se abren los PRs #1 a #14 (backend, frontend, infraestructura, diagramas y documentos) | "Al cerrar la noche" |
| Mié 25, mañana hasta 10:57 | Carlos revisa y aprueba los PRs #1 a #14; se fusionan entre 10:56 y 10:57 | G1 (planeado 08:15 a 10:30) |
| Mié 25, 10:54 a 11:31 | PR #15 (bitácora de IA de Carlos), revisado por Luis y fusionado | — |
| Mié 25, 11:25 | Se abren #16 (catálogo de colonias) y #17 (semilla de 500 reportes) | L4 y L5 |
| Mié 25, 11:42 a 12:08 | Carlos abre los PRs #18 a #26 (aviso de lluvia, zona, administración, consulta, detalle, moderación, avance y tablero) | C3 a C11 |
| Mié 25, 15:03 a 15:20 | Se abren #27 (auditoría de accesibilidad), #28 (bitácora de Carlos) y #29 (despliegue público) | C12, L15 |
| Mié 25, 15:08 a 15:42 | Se fusionan #16, #17, #18, #19, #22, #24, #25 y #20. #23 se fusionó a la rama de #22 y no a `main`; se reabrió como #30 (15:34) | G3 (planeado 20:00) |
| Mié 25, tarde | Despliegue en Neon, Render y Vercel; se comprueban salud de la API, `/docs` y CORS (PR #29) | G2 (planeado 13:00) |
| [PENDIENTE] | Fusión de #21 y #26 a #30; congelamiento de código; etiqueta `v1.0.0` | G3 a G5 |

La revisión de la mañana terminó casi media hora después de lo previsto y el despliegue de humo se movió de las 13:00 a la tarde.
Las historias P1 no se alcanzaron a iniciar al momento de redactar.

### 2.4 Arquitectura

<figure>
<img src="../arquitectura.png" alt="Diagrama de arquitectura: navegador, Vercel, API FastAPI en Render, PostgreSQL en Neon, Nominatim y Open-Meteo">
<figcaption>Figura 1. Arquitectura de Liebre Urbana (<code>docs/arquitectura.png</code>).</figcaption>
</figure>

El navegador descarga la aplicación React desde Vercel y solo habla con la API de FastAPI (en Render, dentro de un contenedor
Docker) por HTTPS y JSON. La API es la única que habla con PostgreSQL (Neon) y con los dos servicios externos: Nominatim de
OpenStreetMap (dirección ↔ coordenadas) y Open-Meteo (probabilidad de lluvia). Así la validación y la autorización ocurren en un
solo lugar. Con Docker Compose las mismas tres piezas corren en una laptop.

### 2.5 Justificación del stack

| Pieza | Elección | Por qué (fuente) |
|---|---|---|
| Interfaz | React 19 + TypeScript + Vite | Lo exigen el cliente y la materia; componentes con props y hooks (React, s. f.); los tipos evitan errores entre pantallas y API |
| API | FastAPI + Pydantic v2 | Validación de entrada y salida con esquemas y documentación OpenAPI en `/docs` sin trabajo extra (FastAPI, s. f.) |
| Datos | PostgreSQL + SQLAlchemy 2 + Alembic | Restricciones, llaves foráneas y triggers en la base (PostgreSQL Global Development Group, s. f.); ORM con relaciones (SQLAlchemy, s. f.); migraciones reproducibles (Alembic, s. f.) |
| Contraseñas y sesión | `bcrypt` y JWT con PyJWT | Hash con sal y token firmado; se evitaron bibliotecas sin mantenimiento (riesgo A03; OWASP Foundation, 2025) |
| Estado en el cliente | `useState`, `useEffect` y un hook propio `useApi` | Lo que enseña la unidad 3, sin librerías de estado extra |
| Contenedores | Docker y Docker Compose | Un solo comando levanta todo el sistema (Docker, s. f.) |
| Configuración | Variables de entorno (`.env`, `.env.example`) | Factor III de The Twelve-Factor App (Wiggins, 2017) |
| Despliegue | Vercel + Render + Neon | Planes gratuitos sin tarjeta, recomendados por la materia (Contreras, 2026) |
| Commits | Conventional Commits en español | Historial legible y regla de la materia (Conventional Commits, s. f.) |

### 2.6 Modelo entidad-relación

<figure>
<img src="../../db/er.png" alt="Diagrama entidad-relación con las 11 tablas de Liebre Urbana">
<figcaption>Figura 2. Modelo entidad-relación (<code>db/er.png</code>).</figcaption>
</figure>

Hay 11 tablas. Las relaciones 1:N principales son sector → colonias, colonia → reportes, usuario → reportes y reporte → historial
de estados. Las N:M son usuarios ↔ reportes por `confirmaciones` (con datos propios: tipo y fecha) y usuarios ↔ colonias por
`usuario_colonias`. Se usó **una sola tabla de reportes** con columna `categoria` (bache o encharcamiento) para que filtros,
paginación y tablero usen la misma consulta; una restricción `CHECK` exige los campos correctos según la categoría.

## 3. Ejecución

### 3.1 Frontend

<div class="borrador" markdown="1">

**[BORRADOR PARA REVISIÓN DE CARLOS]** (redactado a partir del código de `frontend/src/`; Carlos lo corrige y completa).

La aplicación es una SPA con React 19, TypeScript y Vite. `App.tsx` define 16 rutas: públicas (`/`, `/zona`, `/mapa`,
`/reportes/:id`, `/login`, `/registro`, `/privacidad`), del ciudadano (`/reportar`, `/mis-reportes`, `/mis-reportes/:id/editar`,
`/perfil`), del moderador (`/moderacion`), del coordinador (`/admin/colonias`, `/admin/usuarios`, `/tablero`) y la página 404.
`/mapa` y `/perfil` son pantallas provisionales de historias P1. Los grupos privados se protegen con `RutaPrivada`, que manda a
`/login` recordando la ruta de origen; ocultar enlaces no es la seguridad real, porque el servidor vuelve a validar el rol.

Toda pantalla que consume la API usa el hook `useApi`, que devuelve los tres estados que se muestran siempre (carga, error con
"Reintentar" y vacío) y descarta respuestas viejas (fragmento simplificado de `hooks/useApi.ts`):

```tsx
useEffect(() => {
  setCargando(true)
  let vigente = true  // si cambió un filtro o se cerró la pantalla, se ignora la respuesta
  funcion()
    .then((r) => { if (vigente) setDatos(r) })
    .catch((e) => { if (vigente) setError(e.message) })
    .finally(() => { if (vigente) setCargando(false) })
  return () => { vigente = false }
}, [...dependencias, intento])  // "intento" sube con el botón Reintentar
```

El formulario dinámico de HU-02.2 muestra campos distintos según el tipo de daño; la tabla vive en `utils/reportes.ts` y el
servidor vuelve a validar lo mismo:

```ts
const CAMPOS_POR_TIPO = {
  bache: ['tamano', 'profundidad', 'carril'],
  hundimiento: ['tamano', 'carril'],
  grieta: ['tamano', 'carril'],
  alcantarilla_sin_tapa: ['senalizado'], // severidad Alta automática: la pone el servidor
}
```

Los componentes reutilizables (`Campo`, `Boton`, `Alerta`, `Estado`, `Paginacion`, `GrupoRadios`, `TarjetaReporte`) reciben props
y se comparten entre pantallas. Los estilos son hojas externas con variables de color en `estilos/variables.css`, diseño desde
360 px con dos puntos de corte (640 px y 1024 px), foco visible y respeto a `prefers-reduced-motion`. El tipo de reporte se distingue
con ícono y texto, no solo con color. Los límites de los formularios (descripción, contraseña) se piden al backend con
`GET /api/reglas` para no repetirlos.

[PENDIENTE: describir las pantallas de moderación y de administración de colonias (ya en `main`) y las de usuarios y tablero
cuando se fusionen #21 y #26, con la gráfica SVG propia del tablero.]

</div>

### 3.2 Backend

La API está en `backend/app/` y se divide en capas: `routers/` (HTTP, sin reglas de negocio), `services/` (reglas), `models/`
(SQLAlchemy), `schemas/` (Pydantic, uno de entrada y otro de salida) y `core/` (configuración, seguridad, errores y reglas). Todos
los valores de negocio (30 m, 50 m, 6 h, 1 km, 10 reportes por hora, umbral de lluvia de 30 %) viven en `core/reglas.py` y el
frontend los lee con `GET /api/reglas`. Los errores tienen siempre la forma `{"detail": "mensaje en español", "codigo": "ETIQUETA"}`.

Al redactar, `main` tiene **32 endpoints** (contando método y ruta); con los PRs en revisión de usuarios, detalle y tablero llegan
a **37**. [PENDIENTE: recontar en `main` al fusionar.] La autorización por rol es una dependencia que se agrega a
cada ruta protegida (`core/deps.py`, simplificado):

```python
def require_role(*roles: str):
    # el usuario (con su rol y si está suspendido) se lee de la base en cada petición
    def comprobar_rol(usuario: UsuarioActual) -> Usuario:
        if usuario.rol not in roles:
            raise ErrorApi(403, "SIN_PERMISO", "Tu rol no permite realizar esta acción")
        return usuario
    return comprobar_rol
```

La vigencia de los encharcamientos (HU-03.2) se resolvió **sin tareas programadas**: antes de cada consulta, `expirar_vencidos()`
pasa a Histórico los que ya vencieron y deja la fila en el historial como "sistema". En las pruebas el reloj se inyecta para
"adelantar" 6 horas sin esperar. Los duplicados se buscan con la fórmula de Haversine y la confirmación repetida la frena una
restricción única de la base.

Servicios externos: Nominatim (búsqueda y búsqueda inversa) con caché, un pedido por segundo, `User-Agent` genérico y respuesta 503
con mensaje claro si falla (OpenStreetMap Foundation, s. f.); Open-Meteo con caché de 1 hora y `{"disponible": false}` si falla,
para que la interfaz diga "Pronóstico no disponible" y lo demás siga funcionando (Open-Meteo, s. f.).

### 3.3 Base de datos

Una sola migración de Alembic (`db/migrations/versions/0001_esquema_inicial.py`) crea las 11 tablas, los índices y dos triggers de
PostgreSQL: uno impide cambiar `creado_en` de un reporte y otro impide modificar o borrar el historial de estados (regla RN-07).
Según el PR #1, la migración se probó en PostgreSQL 16 con `upgrade`, `downgrade` y `upgrade` otra vez. Los folios
(`BCH-2026-000123`, `ENC-2026-000045`) salen de una tabla de contadores con bloqueo de fila (`SELECT … FOR UPDATE`) para que dos
altas al mismo tiempo no repitan número.

La semilla (`db/seed.py`) es idempotente y carga catálogos, una cuenta por rol, **23 colonias reales** y **500 reportes ficticios**
en 12 semanas con historial coherente. Las colonias salen del Catálogo Nacional de Códigos Postales de Correos de México (s. f.),
descargado el 24 de noviembre de 2026; por los términos de uso de la fuente solo se guarda una muestra, y las coordenadas son
centroides aproximados obtenidos de OpenStreetMap. Todo está documentado en `db/datos/FUENTE.md`.

### 3.4 Seguridad

La revisión de A01 (control de acceso) y A02 del OWASP Top 10:2025 (OWASP Foundation, 2025) está en
[`docs/seguridad-backend.md`](https://github.com/luisreyna060318-alt/liebres-urbanas/blob/main/docs/seguridad-backend.md) y se
comprueba con `backend/tests/test_seguridad.py`. Lo principal:

- Contraseñas con `bcrypt`; el hash no aparece en ninguna respuesta. JWT de 30 minutos firmado con `SECRET_KEY` de entorno; en
  producción el backend no arranca con la clave de ejemplo.
- Rol y suspensión se leen de la base en cada petición; una matriz rol × endpoint prueba cada ruta con cuatro casos (sin sesión,
  ciudadano, moderador, coordinador) y falla si alguien agrega una ruta sin sumarla.
- Solo el autor edita o borra su reporte, y solo en Recibido (403 o 409 en otro caso).
- Privacidad: ninguna respuesta pública trae al autor; las pruebas recorren el JSON y los esquemas de `/docs` buscando campos
  prohibidos.
- CORS limitado a los dominios de Vercel; cabeceras `nosniff`, `X-Frame-Options`, `Referrer-Policy` y, en producción, HSTS.

Pendientes que documentamos: no hay límite de intentos en el login (OWASP A07) y `/docs` es público también en producción.
[PENDIENTE: búsqueda de secretos en todo el historial antes de la etiqueta.]

### 3.5 Contenedores y despliegue

`compose.yaml` incluye `infra/docker-compose.yml` con tres servicios (PostgreSQL, backend y frontend con nginx sin privilegios).
Al arrancar, el backend corre `alembic upgrade head` y la semilla si la base está vacía. Según el PR #3, con la rama integrada
`docker compose up -d --build` terminó en 42 s y los tres contenedores quedaron sanos. [PENDIENTE: prueba cronometrada desde un clon
limpio de `main` antes de la etiqueta, RNF-04.]

En la nube: frontend en Vercel (`https://liebre-urbana.vercel.app`), backend en Render como servicio Docker
(`https://liebre-urbana-api.onrender.com`) y base en Neon con conexión directa. Las claves solo viven en los paneles de cada
servicio; `.env` está en `.gitignore` y `.env.example` trae valores de ejemplo. El 25 de noviembre por la tarde comprobamos que
`/api/health` responde `{"estado":"ok","base_de_datos":"ok"}` y que el frontend responde 200. El plan gratuito de Render "duerme" el
servicio, así que el primer pedido puede tardar; antes de la demo se despierta. La guía paso a paso está en `infra/DEPLOY.md`.
[PENDIENTE: fusionar #29, que agrega las direcciones al README.]

## 4. Evaluación

### 4.1 Pruebas

| Capa | Herramienta | Qué se probó | Resultado real |
|---|---|---|---|
| API | `pytest` + `TestClient` + SQLite en memoria | Registro y login, matriz rol × endpoint, autoría, privacidad, duplicados a 30 y 50 m, una confirmación por persona, vigencia de 6 h y 3 desmentidos, máquina de estados, límite de 10 por hora, geocodificación y clima con la red simulada, zona, semilla | **412 pruebas pasan** en el CI de `main` (corrida del 25-nov sobre el commit `ca8c54f`) |
| Estilo | `ruff` | Backend y `db/` | Sin errores en esa corrida |
| Frontend | Vitest + Testing Library | Validaciones, estados de carga, error y vacío, rutas privadas, formularios de reporte, confirmaciones, zona y aviso de lluvia | **145 pruebas en 18 archivos pasan** en la misma corrida; lint sin advertencias y build correcto |

Las cifras salen del registro de GitHub Actions; no las corrimos de nuevo en local para este reporte. Las pruebas de la API usan
SQLite, así que lo que depende de PostgreSQL (triggers, bloqueos de fila) se comprobó aparte, a mano, según los PRs #1 y #21; el
bloqueo con `with_for_update` de #21 no se ejercita con SQLite y lo dice el propio PR. [PENDIENTE: actualizar los totales con la
corrida de CI de la etiqueta `v1.0.0`.]

### 4.2 Lighthouse y accesibilidad

[PENDIENTE: fusión del PR #27.] El PR #27 trae una auditoría con Lighthouse (categoría Accesibilidad) y axe-core en las 12 vistas
principales, en 360 px y 1280 px: Lighthouse 100 en todas y 0 violaciones de axe, sin desborde horizontal a 360 px. La primera
pasada no salió limpia: había desborde a 360 px en las tablas de administración y un 98 en `/mis-reportes` por el orden de los
encabezados; ambos se corrigieron. Las mediciones se hicieron en una computadora local, sobre `main` más los PRs abiertos, y no en
la URL pública; no se hizo revisión manual con lector de pantalla (W3C, 2023). [PENDIENTE: repetir sobre `main` fusionado y sobre
la URL desplegada, y enlazar `docs/lighthouse/README.md`.]

### 4.3 Problemas encontrados

| Problema | Cómo se detectó | Qué se hizo |
|---|---|---|
| La fila de espera hacia Nominatim no tenía límite: con muchas búsquedas a la vez cada petición ocupaba un hilo y podía dejar sin hilos a la API | Revisión A01/A02 del backend (L11, PR #12) | Espera máxima de 3 s y respuesta 503; lo que está en caché no hace fila |
| Faltaba la cabecera HSTS | Misma revisión | Se agregó solo en producción |
| Condición de carrera en moderación: dos moderadores que validan y rechazan a la vez dejarían dos filas de historial incoherentes | Revisión de Luis en #24 y #25 | Se sugirió bloquear la fila con `with_for_update=True`, pero #24 y #25 se fusionaron sin ese cambio. [PENDIENTE: al redactar, `services/moderacion.py` en `main` sigue leyendo el reporte sin bloqueo] |
| Los formularios de filtros de consulta y tablero se desmontaban al buscar y se perdía el foco del teclado | Revisión de Luis en #22 y #26 | Observación no bloqueante. [PENDIENTE: al redactar, `Consulta.tsx` en `main` sigue montando el formulario con `key`] |
| `hasta=9999-12-31` en la consulta provoca un error 500 | Revisión de Luis en #22 | [PENDIENTE: acotar el rango de fechas] |
| Desborde a 360 px en administración y orden de encabezados en `/mis-reportes` | Auditoría de accesibilidad (#27) | Corregido en #20, #21 y #27 |
| Un PR apilado (#23) se fusionó a la rama de su PR base y no a `main`, porque GitHub no cambió su base al fusionar #22 | Se notó después de fusionar (descripción de #30) | Se abrió #30 con el mismo contenido. [PENDIENTE: fusionar #30] |
| La revisión de la mañana y el despliegue se atrasaron respecto al plan | Cronograma real | El despliegue pasó a la tarde; P1 quedó sin iniciar |

### 4.4 Lecciones aprendidas

- Partir el trabajo en PRs pequeños y apilados permitió revisar 14 PRs en una mañana, pero los PRs apilados tienen trampa: hay que
  confirmar la rama base antes de fusionar (le pasó a #23). Las revisiones más útiles fueron las que corrieron la rama y buscaron
  casos límite (fechas extremas, dos peticiones al mismo tiempo, uso con teclado), no las que solo leyeron el diff.
- Una observación "no bloqueante" en una revisión se olvida fácil: la condición de carrera de moderación llegó a `main` sin
  corregir. Conviene pedir cambios cuando el error afecta datos que no se pueden borrar.
- Poner las reglas en el servidor (rol, autoría, estados) y en la base (restricciones únicas y triggers) evitó depender de que la
  pantalla "se porte bien".
- Medir antes de afirmar: la auditoría de accesibilidad encontró problemas que a simple vista no se veían, y una bitácora afirmó una
  verificación que no se había hecho (sección 5.2).
- El plan de 40 horas fue optimista: el tablero de GitHub Projects y las historias P1 fueron lo primero que se cayó.

### 4.5 Trabajo futuro

Las 8 historias P1 (mapa con Leaflet, exportar CSV y XML con XSD, colonias de interés, puntos recurrentes, resumen por colonia,
catálogos editables, avisos y actualización periódica) y las 6 P2 (fotos con almacenamiento persistente, trayecto, fusionar
duplicados, cuadrillas, enlace municipal y PWA). También: límite de intentos en el login, decidir si `/docs` se apaga en
producción, pruebas de la API contra PostgreSQL real en el CI y revisión manual de accesibilidad con lector de pantalla.

## 5. Uso de IA

### 5.1 Resumen de AI_USAGE.md

La declaración completa está en [`AI_USAGE.md`](https://github.com/luisreyna060318-alt/liebres-urbanas/blob/main/AI_USAGE.md) y en
las bitácoras de [`docs/ai/`](https://github.com/luisreyna060318-alt/liebres-urbanas/tree/main/docs/ai). Seguimos la política de
autoría de la ACM (Association for Computing Machinery, s. f.): la IA no es autora y respondemos por todo el material.

- **Herramientas.** Los dos usamos Claude Code en la aplicación de escritorio de Claude, con Claude Sonnet 5.5 como orquestador y
  agentes de apoyo con Claude Opus 5.5 (backend y revisiones) y Claude Sonnet 5.5 (frontend, infraestructura, semilla, diagramas y
  documentos), cada uno en su propia copia de trabajo de Git.
- **Modo de uso.** Agente que lee y edita archivos y ejecuta comandos. Las acciones que salen de la computadora (push, PR,
  despliegue, descargas) solo con autorización expresa de la persona.
- **Contexto.** `CLAUDE.md` y `docs/plan/` (plan, backlog, contrato de la API, diseño técnico y checklist).
- **Marcado.** Los 113 commits sin merge de todas las ramas del repositorio llevan la línea `Co-Authored-By` con el modelo real.
- [PENDIENTE: `AI_USAGE.md` todavía tiene sin llenar la parte de Carlos (herramienta y modo), la estimación por carpeta (punto 6)
  y la reflexión crítica (punto 7); se completan antes de la etiqueta.]

### 5.2 Reflexión crítica

Casi todo el código de este proyecto lo escribieron agentes de IA a partir de nuestro plan, así que nuestro trabajo principal fue
decidir qué construir, revisar y comprobar. Estos casos, todos registrados en el repositorio, muestran por qué la revisión no se
puede saltar:

1. **Un error que podía tumbar el servidor.** El agente del backend implementó el límite de "un pedido por segundo" a Nominatim con
   un candado sin tiempo máximo de espera. Pasaba las pruebas, pero con muchas búsquedas a la vez cada petición se quedaba esperando
   su turno y ocupaba un hilo del servidor; con suficientes, el resto de la API se quedaba sin hilos. Lo encontró la revisión
   A01/A02 del backend y se corrigió con una espera máxima de 3 s y respuesta 503 (`docs/seguridad-backend.md`). La misma revisión
   encontró que faltaba HSTS.
2. **Una condición de carrera.** En moderación, el código leía el reporte sin bloquear la fila: si dos moderadores validan y
   rechazan a la vez, quedarían dos cambios de estado incoherentes en un historial que, por diseño, no se puede borrar. Lo señaló
   la revisión de #24 y #25, que aun así se fusionaron sin el cambio; en #21 sí se había usado `with_for_update`, o sea que la IA no aplica sola en un lugar lo que ya hizo
   bien en otro.
3. **Accesibilidad que las pruebas no ven.** Los formularios de filtros se volvían a montar en cada búsqueda y el foco del teclado se
   perdía (revisión de #22 y #26). Las pruebas pasaban porque no simulan a alguien que navega solo con teclado.
4. **Una bitácora que afirmaba algo que no pasó.** La fila de la bitácora de Carlos para el tablero decía que se comparó contra
   los 500 reportes en PostgreSQL, pero el PR #26 dice que esa comparación no se hizo (las pruebas usan SQLite). Lo detectó la
   revisión de #28 y se pidió corregir. Es el caso que más nos enseñó: la IA redacta con seguridad lo que "debería" haber pasado.

Lo que aprendimos y no habríamos aprendido igual sin ella: a leer un diff ajeno buscando lo que falta (bloqueos, límites de espera,
fechas extremas) y no solo lo que está, y a desconfiar de cualquier "ya se verificó" sin una evidencia que se pueda abrir. También
aprendimos el costo: con tanto código generado en pocas horas, cada uno tiene que estudiar a fondo lo de la otra persona para la
defensa. [PENDIENTE: que Luis y Carlos revisen y hagan suya esta reflexión, y que se copie al punto 7 de `AI_USAGE.md`.]

## 6. Contribución individual

Cifras del repositorio de trabajo al 25-nov a las 15:45 (hora de Juárez), sin contar commits de merge, obtenidas con
`git shortlog -sn --no-merges` y `gh pr list --state all`. [PENDIENTE: recalcular sobre la etiqueta `v1.0.0`.]

| Integrante | Rol | Tareas principales | Commits (todas las ramas / en `main`) | PRs abiertos (fusionados) | PRs que revisó | % acordado |
|---|---|---|---|---|---|---|
| Luis David Reyna Morisco | Base de datos, backend, frontend base, DevOps | Plan y contrato; API base, modelos, migración y autenticación; geocodificación, reportes, duplicados, encharcamientos y seguridad; frontend base y pantallas de reporte; Docker, CI y despliegue; diagramas; catálogo y semilla | 63 / 62 | 17 (16) | 12 (#15 y #18 a #28) | [PENDIENTE: acordado por el equipo] |
| Carlos Limones Ayala | Consulta, moderación, administración, tablero | Revisión de los 16 PRs de Luis; aviso de lluvia, zona, consulta, detalle, moderación, avance de reparación, administración de colonias y usuarios, tablero; auditoría de accesibilidad | 50 / 30 | 13 (8; #23 se fusionó a una rama, no a `main`) | 16 (todos los de Luis) | [PENDIENTE: acordado por el equipo] |

Todos los commits se hicieron con asistencia de IA (sección 5). Los de Luis se concentran en la noche del 24 y los de Carlos en el
día 25, porque así se repartió el trabajo; la diferencia en `main` se debe a que varios PRs de Carlos siguen en revisión.

## 7. Coevaluación entre pares

Cada integrante califica de 1 a 5 a la otra persona. Puede entregarse en privado al docente; aquí solo va la plantilla vacía.

<div class="junto" markdown="1">

| Evaluador | Evaluado | Compromiso (1 a 5) | Calidad (1 a 5) | Comunicación (1 a 5) | Comentario |
|---|---|---|---|---|---|
| Luis David Reyna Morisco | Carlos Limones Ayala | | | | |
| Carlos Limones Ayala | Luis David Reyna Morisco | | | | |

</div>

## 8. Referencias

<div class="referencias" markdown="1">

Alembic. (s. f.). *Alembic documentation*. https://alembic.sqlalchemy.org/

Association for Computing Machinery. (s. f.). *ACM policy on authorship*. https://www.acm.org/publications/policies/new-acm-policy-on-authorship

Contreras, R. (2026). *Proyecto final: Programación Web (AEB-1055)* [Documento de la materia]. Instituto Tecnológico de Ciudad Juárez.

Conventional Commits. (s. f.). *Conventional Commits 1.0.0*. https://www.conventionalcommits.org/es/v1.0.0/

Correos de México. (s. f.). *Catálogo Nacional de Códigos Postales* [Conjunto de datos]. Recuperado el 24 de noviembre de 2026, de https://www.correosdemexico.gob.mx/SSLServicios/ConsultaCP/CodigoPostal_Exportar.aspx

Docker. (s. f.). *Docker Compose documentation*. https://docs.docker.com/compose/

FastAPI. (s. f.). *FastAPI documentation*. https://fastapi.tiangolo.com/

Fielding, R. T. (2000). *Architectural styles and the design of network-based software architectures* [Tesis doctoral, University of California, Irvine].

mySociety. (s. f.). *FixMyStreet*. https://www.fixmystreet.com/

Open-Meteo. (s. f.). *Weather forecast API*. https://open-meteo.com/en/docs

OpenStreetMap Foundation. (s. f.). *Nominatim usage policy*. https://operations.osmfoundation.org/policies/nominatim/

OWASP Foundation. (2025). *OWASP Top 10:2025*. https://owasp.org/Top10/

PostgreSQL Global Development Group. (s. f.). *PostgreSQL documentation*. https://www.postgresql.org/docs/

React. (s. f.). *React documentation*. https://react.dev/

SQLAlchemy. (s. f.). *SQLAlchemy 2.0 documentation*. https://docs.sqlalchemy.org/en/20/

W3C. (2023). *Web Content Accessibility Guidelines (WCAG) 2.2*. https://www.w3.org/TR/WCAG22/

Waze. (s. f.). *Waze*. https://www.waze.com/

Wiggins, A. (2017). *The Twelve-Factor App*. https://12factor.net/

</div>

<!-- La sección 9 (autoevaluación) se toma de docs/AUTOEVALUACION.md al generar el PDF, para no tener dos versiones. -->
<!-- INCLUIR: ../AUTOEVALUACION.md -->
