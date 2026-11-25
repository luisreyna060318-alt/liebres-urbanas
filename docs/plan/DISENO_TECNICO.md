# Liebre Urbana — Diseño técnico

Este documento es el **contrato** entre las dos personas del equipo: lo que aquí dice cómo se llaman las tablas, los endpoints y
las reglas es lo que ambos construyen. Si algo cambia, se cambia aquí en un PR pequeño y se avisa.

## 1. Arquitectura

```mermaid
flowchart LR
  N[Navegador<br/>React + TypeScript] -->|HTTPS · JSON| A[API FastAPI<br/>Render, Docker]
  A -->|SQLAlchemy| D[(PostgreSQL<br/>Neon)]
  A -->|HTTPS| G[Nominatim<br/>direcciones y coordenadas]
  A -->|HTTPS| C[Open-Meteo<br/>pronóstico de lluvia]
  V[Vercel<br/>archivos estáticos] -.sirve.-> N
```

El navegador **nunca** habla con PostgreSQL ni con los servicios externos: todo pasa por FastAPI, que es donde se valida y se autoriza.
Con Docker Compose, las mismas tres piezas (frontend, backend, PostgreSQL) corren en la laptop.
El diagrama final se exporta a `docs/arquitectura.png` (tarea de Carlos, PR C12).

### Justificación del stack

| Pieza | Elección | Por qué |
|---|---|---|
| Interfaz | React + TypeScript + Vite | Lo exige el cliente (React con TypeScript) y la materia; tipos que evitan errores entre pantallas y API |
| API | FastAPI + Pydantic v2 | Validación y documentación `/docs` automáticas; requisito de la materia |
| Datos | PostgreSQL + SQLAlchemy 2 + Alembic | Relaciones, restricciones e integridad; migraciones reproducibles |
| Contraseñas y sesión | `bcrypt` y JWT con `PyJWT` | Recomendado por la materia; se evitan `passlib` y `python-jose` por falta de mantenimiento |
| Estado en el cliente | `useState`, `useEffect` y un hook propio `useApi` | Lo que enseña la unidad 3; sin librerías de estado que explicar |
| Rutas | `react-router` | Estándar de facto |
| Mapa (P1) | Leaflet + OpenStreetMap | Gratis, sin llave |
| Gráficas | SVG propio | Una sola gráfica de barras; sin dependencia nueva |
| Pruebas | `pytest` (SQLite en memoria) y Vitest | Corren sin Docker y en CI sin servicios extra |
| Despliegue | Vercel + Render + Neon | Gratis, sin tarjeta, recomendado por la materia |

Se agrega una dependencia nueva solo avisando y justificando (riesgo A03 del OWASP Top 10:2025).

## 2. Estructura del monorepo

```
liebre-urbana/
├── frontend/              React (Vite) · src/{paginas,componentes,api,hooks,estilos} · Dockerfile · vercel.json
├── backend/
│   ├── app/{routers,services,models,schemas,core}
│   ├── tests/
│   ├── Dockerfile · entrypoint.sh · requirements.txt · requirements-dev.txt
├── db/                    migraciones Alembic · seed.py · datos/colonias.csv · er.png
├── infra/                 docker-compose.yml · DEPLOY.md
├── docs/                  plan/ · ai/ · REPORTE.pdf · AUTOEVALUACION.md · arquitectura.png
├── .github/               workflows/ci.yml · CODEOWNERS · pull_request_template.md
├── .env.example · AI_USAGE.md · CLAUDE.md · README.md
```

Capas del backend: **router** (HTTP, sin lógica) → **service** (reglas de negocio) → **model** (SQLAlchemy). Esquemas Pydantic
distintos para entrada y salida; el de salida pública **nunca** incluye al autor.

## 3. Modelo de datos

```mermaid
erDiagram
  SECTORES ||--o{ COLONIAS : agrupa
  COLONIAS ||--o{ REPORTES : ubica
  USUARIOS ||--o{ REPORTES : crea
  TIPOS_DANO ||--o{ REPORTES : clasifica
  MOTIVOS_RECHAZO ||--o{ REPORTES : justifica
  REPORTES ||--o{ HISTORIAL_ESTADOS : registra
  USUARIOS ||--o{ HISTORIAL_ESTADOS : realiza
  USUARIOS ||--o{ CONFIRMACIONES : emite
  REPORTES ||--o{ CONFIRMACIONES : recibe
  USUARIOS ||--o{ USUARIO_COLONIAS : elige
  COLONIAS ||--o{ USUARIO_COLONIAS : es_elegida
  USUARIOS ||--o{ NOTIFICACIONES : recibe
  REPORTES ||--o{ NOTIFICACIONES : origina

  SECTORES { int id PK  string nombre UK }
  COLONIAS { int id PK  string nombre  int sector_id FK  bool activa  float lat  float lon  string fuente }
  USUARIOS { int id PK  string nombre  string correo UK  string password_hash  string rol  bool activo  datetime acepto_privacidad_en  datetime creado_en }
  TIPOS_DANO { int id PK  string codigo UK  string nombre  bool activo }
  MOTIVOS_RECHAZO { int id PK  string codigo UK  string nombre  bool pide_explicacion  bool activo }
  REPORTES { int id PK  string folio UK  string categoria  int tipo_dano_id FK  int autor_id FK  int colonia_id FK  string calle  float lat  float lon  string descripcion  string severidad  string tamano  string profundidad  string carril  bool senalizado  string nivel_agua  bool hay_riesgo  string estado  int confirmaciones  datetime creado_en  datetime vigente_hasta  date fecha_reparacion  int motivo_rechazo_id FK  string motivo_texto }
  HISTORIAL_ESTADOS { int id PK  int reporte_id FK  string estado_anterior  string estado_nuevo  int actor_id FK  string comentario  datetime creado_en }
  CONFIRMACIONES { int id PK  int reporte_id FK  int usuario_id FK  string tipo  datetime creado_en }
  USUARIO_COLONIAS { int usuario_id PK  int colonia_id PK }
  NOTIFICACIONES { int id PK  int usuario_id FK  int reporte_id FK  string mensaje  bool leida  datetime creado_en }
  FOLIO_CONTADORES { string prefijo PK  int anio PK  int ultimo }
```

**Relaciones.** 1:N: sector→colonias, colonia→reportes, usuario→reportes, reporte→historial. **N:M**: usuarios↔reportes por
`confirmaciones` (con datos propios: tipo y fecha) y usuarios↔colonias por `usuario_colonias`. La primera ya cumple el
requisito de la materia aunque la segunda (HU-01.4, P1) se recorte.

**Una sola tabla de reportes** con columna `categoria` (`bache` o `encharcamiento`): los filtros, la paginación, el tablero y la
exportación quedan en una sola consulta. Los campos propios de cada categoría son opcionales y una restricción `CHECK` exige los
correctos según la categoría.

### Restricciones de integridad

| Restricción | Dónde | Historia |
|---|---|---|
| `usuarios.correo` único (sin distinguir mayúsculas) | Índice único sobre `lower(correo)` | HU-01.1 CA2 |
| `confirmaciones` única por `(reporte_id, usuario_id)` | `UniqueConstraint` | HU-02.3 CA3, HU-03.3 CA2 |
| `colonias` única por `(sector_id, nombre)` | `UniqueConstraint` | HU-06.1 CA3 |
| `reportes.folio` único; el consecutivo sale de `folio_contadores` con bloqueo de fila | `UniqueConstraint` + `SELECT … FOR UPDATE` | RN-03 |
| `reportes.creado_en` no cambia nunca | Trigger en PostgreSQL + el esquema de entrada no lo acepta | RN-10 |
| `historial_estados` solo se inserta (`actor_id` NULL = "sistema") | Trigger que rechaza `UPDATE` y `DELETE` + evento de SQLAlchemy + ninguna ruta. Única excepción: el borrado en cascada al eliminar el reporte completo (HU-02.5, solo en Recibido) | RN-07, HU-05.2 CA4 |
| `descripcion` ≤ 500 caracteres | `CHECK` + Pydantic | HU-02.2 CA4 |
| Categoría y campos coherentes | `CHECK` | HU-02.2 |
| Índices en `(categoria, estado)`, `(colonia_id)`, `(creado_en)`, `(lat, lon)` | Migración | RNF-06 |

### Estados (RN-05 y RN-06)

```mermaid
stateDiagram-v2
  direction LR
  state "Bache" as B {
    [*] --> recibido
    recibido --> validado: moderador
    recibido --> rechazado: moderador
    validado --> en_reparacion: moderador o coordinador
    en_reparacion --> reparado: moderador o coordinador (fecha de reparación)
    reparado --> [*]
    rechazado --> [*]
  }
  state "Encharcamiento" as E {
    [*] --> activo
    activo --> historico: 6 h sin confirmaciones, o 3 desmentidos
    activo --> rechazado: moderador, en cualquier momento
    historico --> rechazado: moderador, en cualquier momento
  }
```

Valores guardados: `recibido`, `validado`, `en_reparacion`, `reparado`, `rechazado` (baches) y `activo`, `historico`, `rechazado`
(encharcamientos). El estado Programado (HU-05.4) y el rol enlace municipal quedan fuera (P2). Cualquier otro salto responde 409.
Los cambios los hace una sola función, `registrar_cambio_estado()`, que valida el salto, actualiza el reporte y agrega la fila del
historial en la misma transacción.

## 4. Reglas de negocio y valores (documentados en un solo lugar)

El cliente permite ajustar las cifras si se documentan y se respetan en toda la plataforma. Todas viven en
`backend/app/core/reglas.py`, y el frontend las pide al backend (`GET /api/reglas`) en lugar de repetirlas.

| Regla | Valor | Origen |
|---|---|---|
| Distancia para detectar duplicado de bache | 30 m | Cliente |
| Distancia para detectar duplicado de encharcamiento | 50 m | Cliente |
| Vigencia de un encharcamiento | 6 h desde la creación o la última confirmación | Cliente |
| Desmentidos para cerrar un encharcamiento | 3 personas distintas | Cliente |
| Radio de "¿Cómo está mi zona?" | 1 km | Cliente |
| Reportes por cuenta | 10 por hora (se cuenta en la base de datos) | Cliente |
| Tamaños de página | Mis reportes 10; consulta 20; catálogos y usuarios 10 | Cliente / equipo |
| Descripción | ≤ 500 caracteres | Cliente |
| Contraseña | ≥ 8 caracteres, con letras y números | Cliente |
| Inactividad de la sesión | **30 minutos** | Equipo |
| Umbral del aviso de lluvia | Probabilidad máxima ≥ **30 %** en las próximas 12 h | Equipo |
| Caché del pronóstico | 1 hora | Cliente |
| Punto recurrente (P1) | ≥ 3 días distintos del año en 50 m | Cliente |
| Zona horaria | `America/Ciudad_Juarez` | RN-02 |

**Severidad del bache** (la calcula el servidor): alcantarilla sin tapa = Alta; tamaño grande o profundidad alta = Alta;
tamaño mediano = Media; los demás = Baja.

**Municipio (RN-01).** El servidor valida que las coordenadas caigan dentro de un rectángulo que cubre el municipio de Juárez
(valores por verificar contra el Marco Geoestadístico de INEGI al implementar L5 y registrar la fuente). Es una validación
aproximada, simple y que funciona sin internet; Nominatim solo ayuda a elegir calle y colonia.

### Interpretaciones que se anotan en el reporte

1. "Vigencia actual" de HU-03.3 CA2: una persona responde **una sola vez** por encharcamiento mientras esté activo.
2. Una persona tiene un solo rol: moderador y coordinador no crean ni confirman reportes.
3. Las confirmaciones de un bache empiezan en 0 (el autor no cuenta) y el autor no confirma su propio reporte.
4. La consulta pública oculta los rechazados; moderador y coordinador sí los pueden ver filtrando por estado. El tablero
   y la consulta usan la **misma función de filtrado**, por eso coinciden (HU-07.1 CA5).
5. La longevidad de un bache son los días desde `creado_en` hasta `fecha_reparacion` o, si sigue abierto, hasta hoy.

## 5. API REST

Prefijo `/api`. Documentación automática en `/docs`. Paginación: `?pagina=1&tam=20` → `{items, total, pagina, tam}`.
Errores: `{"detail": "mensaje en español", "codigo": "ETIQUETA"}` con 400, 401, 403, 404, 409, 422 o 429 según el caso.

**Roles:** P = público, C = ciudadano, M = moderador, K = coordinador.

| # | Método y ruta | Quién | Historia | Dueño |
|---|---|---|---|---|
| 1 | `GET /health` | P | RNF-03 | L |
| 2 | `POST /auth/registro` (201) | P | HU-01.1 | L |
| 3 | `POST /auth/login` | P | HU-01.2 | L |
| 4 | `POST /auth/refresh` | C, M, K | HU-01.2 CA4 | L |
| 5 | `GET /auth/yo` | C, M, K | HU-01.2 | L |
| 6 | `GET /reglas` | P | Valores documentados | L |
| 7 | `GET /colonias` (L1b entrega la lectura básica para los formularios; C8 agrega búsqueda y paginación) | P | HU-06.1, formularios | C |
| 8 | `POST /colonias` (201) | K | HU-06.1 | C |
| 9 | `PUT /colonias/{id}` (incluye `activa`) | K | HU-06.1 | C |
| 10 | `DELETE /colonias/{id}` (204, o 409 si tiene reportes) | K | HU-06.1 CA2 | C |
| 11 | `GET /sectores`, `POST /sectores`, `PUT /sectores/{id}` | P / K | HU-06.1 | C |
| 12 | `GET /tipos-dano`, `GET /motivos-rechazo` | P | HU-02.2, HU-05.1 | L |
| 13 | `GET /geo/buscar?q=` | P | HU-02.1, HU-03.1, HU-04.3 | L |
| 14 | `GET /geo/inversa?lat=&lon=` | P | HU-02.1 CA1 | L |
| 15 | `GET /clima/aviso` | P | HU-08.1 | C |
| 16 | `POST /reportes/baches` (201) | C | HU-02.1, 02.2 | L |
| 17 | `POST /reportes/encharcamientos` (201) | C | HU-03.1 | L |
| 18 | `GET /reportes/cercanos?categoria=&lat=&lon=` | C | HU-02.3, HU-03.1 CA4 | L |
| 19 | `POST /reportes/{id}/confirmaciones` (201) | C | HU-02.3, HU-03.3 | L |
| 20 | `GET /mis-reportes` | C | HU-02.5 | L |
| 21 | `PUT /reportes/{id}` | C (autor, Recibido) | HU-02.5 | L |
| 22 | `DELETE /reportes/{id}` (204) | C (autor, Recibido) | HU-02.5 | L |
| 23 | `GET /reportes` (filtros, búsqueda, paginación) | P | HU-04.1, 04.2 | C |
| 24 | `GET /reportes/{id}` (detalle e historial) | P | HU-04.4 | C |
| 25 | `GET /zona?lat=&lon=` | P | HU-04.3 | C |
| 26 | `GET /moderacion/bandeja` | M | HU-05.1 | C |
| 27 | `POST /reportes/{id}/validar` | M | HU-05.1 | C |
| 28 | `POST /reportes/{id}/rechazar` | M | HU-05.1 | C |
| 29 | `POST /reportes/{id}/estado` | M, K | HU-05.2 | C |
| 30 | `GET /usuarios` | K | HU-06.2 | C |
| 31 | `PUT /usuarios/{id}/rol` | K | HU-06.2 | C |
| 32 | `PUT /usuarios/{id}/suspension` | K | HU-06.2 | C |
| 33 | `GET /tablero` | K | HU-07.1 | C |

Con P1: `GET/PUT /yo/colonias` (HU-01.4), `GET /puntos-recurrentes` (HU-03.4), `POST/PUT /tipos-dano` y `/motivos-rechazo`
(HU-06.3), `GET /notificaciones` y `POST /notificaciones/{id}/leer` (HU-08.2), `GET /colonias/{id}/resumen` (HU-07.2),
`GET /reportes/exportar?formato=csv|xml` (HU-07.3).

Son **36 endpoints en P0** (contando por método y ruta) frente a los 12 que pide la materia.

## 6. Servicios externos

| Servicio | Uso | Cuidados |
|---|---|---|
| **Nominatim** (OpenStreetMap) | `buscar` convierte una dirección en coordenadas, calle y colonia; `inversa` convierte coordenadas en calle y colonia | Máximo 1 pedido por segundo, encabezado `User-Agent` genérico (nunca un correo personal), búsqueda restringida a Ciudad Juárez, caché en memoria, tiempo de espera de 5 s, no se busca "mientras se escribe". Si falla: mensaje claro y captura manual |
| **Open-Meteo** | Probabilidad de lluvia por hora en las próximas 12 h para Juárez, sin llave | Caché de 1 h; si falla, `{"disponible": false}` y la interfaz muestra "Pronóstico no disponible" |

La colonia se asigna igualando el nombre devuelto con el catálogo oficial; si no coincide, la persona la elige en una lista.
En las pruebas ambos servicios se simulan.

## 7. Seguridad (OWASP A01 y A02)

| Medida | Dónde |
|---|---|
| Contraseñas con `bcrypt`; el hash no aparece en ningún esquema de salida | `core/security.py`, esquemas |
| JWT de 30 min que firma `SECRET_KEY` (variable de entorno); el backend se niega a arrancar en producción con la clave de ejemplo | `core/config.py` |
| **Autorización en el servidor**: dependencia `require_role(...)` en cada endpoint protegido y comprobación de autoría en editar y borrar | `routers/`, `services/` |
| El rol y el estado `activo` del usuario se leen de la base de datos en cada petición | dependencia `usuario_actual` |
| Mensaje único en el login fallido (no revela si fue el correo o la contraseña) | `services/auth.py` |
| CORS limitado al dominio del frontend (`CORS_ORIGINS`) | `main.py` |
| Límite de 10 reportes por hora y por cuenta (429) | `services/reportes.py` |
| Sin secretos en Git: `.env` ignorado, `.env.example` con valores de ejemplo, claves solo en los paneles de Render y Vercel | `.gitignore` |
| Consultas con parámetros de SQLAlchemy (sin SQL armado a mano) | modelos y servicios |
| Cabeceras de seguridad en Vercel (`X-Content-Type-Options`, `Content-Security-Policy`…) | `frontend/vercel.json` |
| Privacidad: los esquemas públicos no incluyen autor; la exportación y el resumen tampoco | esquemas y pruebas |
| Aviso de privacidad conforme a la Ley Federal de Protección de Datos Personales en Posesión de los Particulares | página `/privacidad` |

## 8. Variables de entorno

| Variable | Dónde | Ejemplo / nota |
|---|---|---|
| `DATABASE_URL` | backend | `postgresql+psycopg://usuario:clave@host/bd` (Neon: `?sslmode=require`) |
| `SECRET_KEY` | backend | Cadena aleatoria larga; Render la genera |
| `CORS_ORIGINS` | backend | URL del frontend, separadas por comas |
| `ENTORNO` | backend | `desarrollo` o `produccion` |
| `SEED_ON_START` | backend | `true` para cargar los datos de demo si la base está vacía |
| `VITE_API_URL` | frontend | URL pública del backend |

`.env.example` solo trae valores de ejemplo; el `.env` real nunca se sube.

## 9. Datos de demostración (RNF-09)

- **Colonias**: al menos 20 reales de Ciudad Juárez, tomadas de un catálogo oficial de asentamientos (SEPOMEX/Correos de México o
  INEGI), con la fuente citada en `db/datos/FUENTE.md` y en el reporte. Los sectores son agrupaciones de la asociación (no son
  oficiales); se documenta el criterio.
- **Reportes**: 500 ficticios repartidos en 12 semanas, con generador de semilla fija (siempre salen iguales), mezcla de baches
  (en todos los estados, con su historial coherente con RN-05) y encharcamientos (la mayoría históricos y algunos recientes).
- **Cuentas**: una por rol (ciudadano, moderador, coordinador), con correos ficticios `@liebreurbana.test` y una contraseña de
  demostración **pública y distinta de cualquier contraseña real**, que se escribe en el README.
- La semilla es idempotente: solo carga si la tabla está vacía. Para la demo se crea un encharcamiento nuevo en vivo.

## 10. Estrategia de pruebas

| Capa | Herramienta | Qué cubre | Meta |
|---|---|---|---|
| API | `pytest` + `TestClient` + SQLite en memoria | Registro y login (CA1 a CA4), matriz rol × endpoint (401 y 403), duplicados a 30 y 50 m, una confirmación por persona, vigencia de 6 h y 3 desmentidos, máquina de estados, historial inalterable, límite de 10 por hora, privacidad de la respuesta pública, filtros y paginación, coincidencia tablero–consulta | ≥ 25 pruebas, de ellas ≥ 8 endpoints y varios protegidos |
| Frontend | Vitest | Validaciones de formularios, componentes de estado (carga, error, vacío) | ≥ 6 pruebas |
| Manual | Lista de la demo | Recorridos de cada rol, 360 px, teclado | Antes de la etiqueta |
| Accesibilidad | Lighthouse y axe | Vistas principales | ≥ 90 |

CI (GitHub Actions, en cada push y PR): `ruff check`, `pytest`, lint y build del frontend, Vitest. La insignia va en el README.

## 11. Frontend: rutas y estados

Rutas (más de las 4 que pide la materia): `/` (consulta de reportes), `/zona`, `/mapa` (P1), `/reportes/:id`, `/login`, `/registro`,
`/privacidad`, `/reportar` (ciudadano), `/mis-reportes` (ciudadano), `/perfil` (ciudadano), `/moderacion` (moderador),
`/admin/colonias`, `/admin/usuarios` y `/tablero` (coordinador).

Toda pantalla que consume la API usa el hook `useApi`, que devuelve `{ datos, cargando, error }`, y muestra los tres estados:
**carga** (esqueleto o texto), **error** (mensaje con botón "Reintentar") y **vacío** (mensaje con la siguiente acción). Los
formularios validan en el cliente (con los mismos límites que el servidor, tomados de `GET /api/reglas`) y el servidor vuelve a
validar. El token se guarda en `sessionStorage`; los 401 llevan a `/login` conservando la ruta de origen.

HTML semántico en cada vista (`header`, `nav`, `main`, `section`, `footer`), `label` en cada campo, texto alternativo, foco visible,
y el tipo de reporte se distingue con **ícono y texto** además del color.
