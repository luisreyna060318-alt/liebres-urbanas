# Revisión de seguridad del backend (A01 y A02)

Revisión hecha en la rama L11 sobre todos los endpoints que existen hasta L10 (cuenta, catálogos, ubicación y reportes
del ciudadano). La comprobación automática está en `backend/tests/test_seguridad.py`.

En OWASP Top 10, A02 es "Fallas criptográficas" en la edición 2021 y "Configuración de seguridad incorrecta" en la 2025;
se revisaron los dos temas.

## A01 — Control de acceso roto

| Qué se revisó | Resultado |
|---|---|
| Cada endpoint protegido usa `require_role(...)` o `usuario_actual` en el servidor | Correcto. La matriz rol × endpoint prueba los 17 endpoints con 4 casos (sin sesión, ciudadano, moderador, coordinador). Una prueba falla si se agrega una ruta y no se suma a la matriz |
| El 403 de rol llega antes de validar el cuerpo | Correcto: un moderador recibe 403 aunque mande datos inválidos (no aprende nada de los campos) |
| Rol y suspensión se leen de la base en cada petición | Correcto: con un token todavía vigente, la suspensión da 403 `CUENTA_SUSPENDIDA` y el cambio de rol surte efecto en la siguiente petición |
| Autoría al editar y borrar (`PUT`/`DELETE /api/reportes/{id}`) | Correcto: otra persona recibe 403 `SIN_PERMISO`; tras `recibido`, 409 y el reporte nunca se borra (RN-07) |
| `GET /api/mis-reportes` solo devuelve lo propio | Correcto (filtro por `autor_id` del token, nunca por un parámetro) |
| Confirmar el reporte propio, o dos veces | 403 `ES_TU_REPORTE` y 409 `YA_CONFIRMADO`; la restricción única de la base frena dos clics simultáneos |
| Privacidad (RN-04): ninguna respuesta pública trae al autor | Correcto: los serializadores copian campo por campo; las pruebas recorren el JSON de todas las respuestas y los esquemas de `/docs` buscando `autor_id`, `correo`, `actor_id`, etc. El 409 de duplicado tampoco revela al autor del reporte cercano |

## A02 — Criptografía y configuración

| Qué se revisó | Resultado |
|---|---|
| Contraseñas con bcrypt; el hash nunca sale | Correcto: ninguna respuesta (ni registro ni login) contiene el hash ni la contraseña |
| JWT firmado con `SECRET_KEY` de entorno; algoritmo fijo (sin `alg: none`); token vencido o alterado → 401 | Correcto |
| En producción no arranca con la clave de ejemplo | Correcto (`core/config.py`) |
| CORS limitado a `CORS_ORIGINS` (nunca `*`) | Correcto |
| Cabeceras de seguridad | `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy` y `Cache-Control: no-store` ya estaban. **Faltaba HSTS**: se agregó solo en producción |
| Errores 500 sin detalles técnicos | Correcto (`core/errores.py`) |
| Nominatim: User-Agent genérico, sin datos personales en la URL | Correcto: solo viaja el texto de la dirección o las coordenadas |

## Qué se corrigió

1. `fix(seguridad)`: cabecera `Strict-Transport-Security` en producción.
2. `fix(geo)`: la fila de espera hacia Nominatim tenía turno ilimitado; con muchas búsquedas a la vez cada petición ocupaba un
   hilo del servidor esperando y podía dejar sin hilos al resto de la API. Ahora espera como máximo 3 s (`GEO_ESPERA_MAX_S`)
   y responde 503; lo que ya está en caché no hace fila.

## Pendientes (fuera de A01/A02 o decisión del equipo)

- No hay límite de intentos en `POST /api/auth/login` (fuerza bruta, OWASP A07). Sugerencia: contar intentos fallidos por
  correo en la base, igual que el límite de reportes por hora.
- `/docs` y `/openapi.json` quedan públicos también en producción. Se dejan para la revisión del proyecto; se pueden apagar con
  `FastAPI(docs_url=None, openapi_url=None)` si el equipo lo decide.
- Los endpoints de moderación, administración y tablero (Carlos) deben sumarse a la matriz de `test_seguridad.py` al llegar.

## Revisión de seguridad de las historias C3 a C11 y los arreglos posteriores (26-nov-2026)

Alcance: todo lo que llegó a `main` después de la revisión de arriba (L1 a L11): consulta pública y detalle (C3, C4), zona
(C5), moderación (C6), avance de reparación (C7), administración de colonias y sectores (C8) y de usuarios (C9), tablero
(C10), aviso de lluvia (C11) y los arreglos #33, #34, #35, #81 a #84 y #86. Referencia: OWASP Top 10:2025. Es una revisión
de **solo lectura**: no se cambió código; cada hallazgo trae el arreglo propuesto y queda "abierto".

### Método

1. Lectura de los 12 routers de `backend/app/routers/`, de `core/` (deps, security, config, errores), de los servicios y
   esquemas de salida, de `frontend/vercel.json`, `render.yaml`, los Dockerfiles y `.github/workflows/`. Se contrastó con
   `DISENO_TECNICO.md` (sección 5) y `CONTRATO_API.md` (secciones 7 a 14).
2. Pruebas en vivo **solo locales**: base desechable en el PostgreSQL de Docker (migrada y sembrada con `db/seed.py`),
   uvicorn en `127.0.0.1:8100` y un script propio con `httpx` (fuera del repositorio) que hizo 251 comprobaciones más un
   script de carreras. Nada se probó contra los sitios desplegados. La base se borró al terminar.
3. `npm audit --omit=dev` y `npm audit` en `frontend/`: **0 vulnerabilidades**. Python: no hay herramienta de auditoría
   instalada (`pip-audit` no está y no se instaló), así que solo se revisó a mano que cada paquete de `requirements.txt` se
   use y sea conocido y mantenido (fastapi, uvicorn, sqlalchemy, alembic, psycopg, pydantic-settings, bcrypt, PyJWT,
   email-validator, httpx, tzdata): todos se usan, ninguno sospechoso.
4. Barrido de secretos en el árbol y en **todo** el historial (`git log -p --all`, 217 commits): cadenas de conexión con
   usuario y clave, `SECRET_KEY=` largas, `ghp_`/`github_pat_`, `AKIA`, llaves privadas, JWT, hosts reales de Neon y
   llaves de Render. **Ninguna coincidencia real**: solo los valores de ejemplo (`usuario:clave`, `liebre:liebre`,
   `cambia-esta-...`, `ep-xxxx`). Nunca se versionó un `.env`, `.pem` ni `.key`.
5. Las suites relacionadas (`test_seguridad`, `test_admin_usuarios`, `test_admin_catalogos`, `test_avance_reparacion`)
   pasan: 229 pruebas.

### Hallazgos

| Id | Severidad | Archivo y línea | Descripción | Evidencia | Arreglo propuesto | Estado |
|---|---|---|---|---|---|---|
| S1 | Media | `services/validaciones.py:35-50` | El límite de 10 reportes por hora se salta con peticiones **simultáneas**: se cuenta y después se inserta, sin bloqueo (A06). Es el único freno al abuso de altas | Ráfaga de 15 `POST /api/reportes/baches` en paralelo con la misma cuenta: **15 × 201** y 15 reportes guardados | Al inicio de `validar_limite_horario`, bloquear la fila de la persona: `db.get(Usuario, autor.id, with_for_update=True)` (serializa las altas de esa cuenta; el conteo ya ve las anteriores) | corregido en #94 (bloqueo de la fila del usuario; 15 altas simultáneas dan 10 creadas y 5 rechazadas) |
| S2 | Media | `services/encharcamientos.py:101-109` y `POST /api/auth/registro` | Cualquiera puede **cerrar un encharcamiento ajeno** (pasa a «historico» y desaparece de la zona y la consulta de activos) con 3 cuentas recién creadas: el registro no tiene límite ni verificación de correo y basta con 3 «ya no hay agua» (A06). El moderador no puede reabrirlo | Script: 1 encharcamiento activo + 3 cuentas nuevas con `ya_no_hay` → `estado=historico` | Decisión de diseño: contar el desmentido solo de cuentas con cierta antigüedad o actividad (por ejemplo, con un reporte propio), limitar registros por IP o permitir al moderador devolverlo a «activo». Documentarlo como riesgo aceptado si no se cambia | abierto |
| S3 | Baja | `services/reportes.py:136` (`_propio_y_editable`) | Carrera de tiempo (TOCTOU) entre el autor y el moderador: el autor lee «recibido» **sin bloqueo**; si un moderador valida en ese instante, el `DELETE` del autor espera al bloqueo y después **borra un reporte ya validado** junto con su historial (por la cascada que el trigger permite), contra RN-07. El moderador recibe 500 (`ObjectDeletedError` en `services/moderacion.py:97`, después del commit) | 32 intentos validar ∥ borrar/editar: **5 reportes validados terminaron borrados** (validar=500, borrar=204, detalle=404). La edición simultánea tiene la misma causa, pero no se distingue por observación de un orden legítimo | `db.get(Reporte, reporte_id, with_for_update=True, populate_existing=True)` en `_propio_y_editable` (igual que `obtener_reporte_para_cambiar`): el autor espera y relee «validado» → 409 | corregido en #94 (el reporte se relee con bloqueo; el autor recibe 409) |
| S4 | Baja | Ids enteros sin tope: `routers/consulta.py:46-47,81`, `routers/reportes.py:105,144,156`, `routers/moderacion.py:40,52,61,92`, `routers/usuarios.py:41,53`, `routers/tablero.py:28`, `routers/admin_catalogos.py` y `colonia_id` de los esquemas de entrada | Un número mayor que `integer` de PostgreSQL (por ejemplo `99999999999`) llega a la base y responde **500** `ERROR_INTERNO` en lugar de 404/422 (A05/A10). No filtra información (el cuerpo es el genérico) pero ensucia el log y lo puede disparar cualquiera sin sesión | `GET /api/reportes/99999999999`, `?colonia_id=99999999999`, `?sector_id=...`, `/api/tablero?sector_id=...`, confirmar, alta con `colonia_id`, `PUT /api/usuarios/99999999999/rol`, bandeja: **los 9 casos dieron 500** | Un tipo común `IdBD = Annotated[int, Field(ge=1, le=2_147_483_647)]` en rutas, `Query` y esquemas de entrada; también tope en `leer_token` (`core/security.py:62`, un `sub` enorme da 500, pero solo con la clave) | corregido en #94 (ids acotados; 422 en vez de 500) |
| S5 | Baja | `services/usuarios.py:28-47`, `services/catalogos.py` | Sin rastro de auditoría de las acciones del coordinador (A09): cambio de rol, suspensión, alta/edición/borrado de colonias y sectores no guardan quién ni cuándo. Tampoco se registran eventos de seguridad (logins fallidos, 403) más allá de la línea de acceso de uvicorn | Revisión de código; el log solo muestra `"PUT /api/usuarios/38/rol" 200` | Un `log.info("rol de %s: %s -> %s por %s", ...)` con ids (sin correos), o una tabla de bitácora (migración de Luis) | abierto |
| S6 | Baja | `backend/requirements.txt`, `.github/workflows/*.yml`, Dockerfiles | Cadena de suministro (A03): solo se fijan las dependencias directas de Python (starlette, pydantic, anyio… quedan libres y sin hashes); las acciones usan etiquetas (`@v4`, `@v5`) y no SHA; las imágenes base usan etiqueta y no digest | Revisión de archivos | `pip-compile --generate-hashes` (o un `requirements.lock`), fijar acciones por SHA y activar Dependabot | abierto |
| S7 | Informativa | `services/catalogos.py:26` | `GET /api/colonias?q=%` usa `contains` **sin** `autoescape`: `%` y `_` funcionan como comodín. No es inyección (va como parámetro) y el catálogo es público | `q=%` → 32 colonias (todas); en reportes y usuarios `q=%` → 0 | `contains(..., autoescape=True)` como en consulta y usuarios | corregido en #94 (`autoescape` en la búsqueda de colonias) |
| S8 | Informativa | `core/errores.py:152` | El 500 guarda la traza con `[parameters: ...]` de SQLAlchemy. Hoy solo se vieron ids, pero un error en una consulta con correo o calle los dejaría en el log de Render | Log local: 20 líneas `[parameters: {'pk_1': ...}]` | Aceptable para el proyecto; si se quiere, `create_engine(..., hide_parameters=True)` en producción | abierto |
| S9 | Informativa | `main.py` / `entrypoint.sh:20` | Sin límite de tamaño del cuerpo en la API: un JSON de 20 MB se lee completo (respondió 422 por la longitud del campo). En Render el proxy pone su propio tope | `POST /api/auth/login` con 20 MB → 422 en 0.1 s (local) | Opcional: rechazar `Content-Length` > 1 MB en el middleware | abierto |
| S10 | Informativa | `frontend/vercel.json` | CSP correcta (`connect-src` solo la API de Render, `img-src` solo teselas de OSM, `frame-ancestors 'none'`), pero con `style-src 'unsafe-inline'` y sin HSTS propio (Vercel lo agrega en sus dominios; no se verificó porque no se probó nada desplegado). El token vive en `sessionStorage` (`frontend/src/api/sesion.ts`): un XSS lo leería; la CSP sin `unsafe-inline` en scripts lo mitiga | Revisión de archivos | Quitar `unsafe-inline` de estilos si la interfaz no lo necesita; agregar `Strict-Transport-Security` explícito | abierto |
| S11 | Informativa | `routers/sistema.py:29` | `/api/health` publica los 7 caracteres del commit. El repositorio es público, así que no revela nada nuevo; sí dice qué versión exacta corre | `{"estado":"ok","base_de_datos":"ok","version":"local"}` | Aceptado (sirve al flujo de despliegue #86) | abierto |
| S12 | Informativa | `tests/test_seguridad.py:74,79`, `docs/plan/DISENO_TECNICO.md` sección 5 | `RUTAS_PROBADAS_APARTE` se define dos veces (la primera no se usa). La tabla de endpoints del diseño no lista `GET /api/moderacion/seguimiento` (sí está en el contrato 10.4). `GET /api/geo/inversa` no se probó en vivo (llama a Nominatim) | Revisión de archivos | Borrar la primera definición; agregar la fila al diseño | corregido en #94 |
| K1 | Media (conocido) | `services/auth.py:59` | Sin límite de intentos en `POST /api/auth/login` (A07). Sigue igual que en la revisión anterior | 30 intentos fallidos seguidos → 30 × 401, ningún 429; la cuenta sigue entrando | El de la revisión anterior: contar fallos por correo en la base y responder 429 | abierto (conocido) |
| K2 | Baja (conocido) | `main.py:23` | `/docs` y `/openapi.json` públicos también en producción (A02) | Ambos 200 sin sesión | `FastAPI(docs_url=None, openapi_url=None)` si `settings.es_produccion` | abierto (conocido) |
| K3 | Baja (conocido) | `services/catalogos.py:170-178` | Unicidad de nombres de sector y colonia sin distinguir mayúsculas solo en el servicio; la base compara exacto (carrera «Centro»/«CENTRO») | Documentado en el código | Índice único sobre `lower(nombre)` (migración de Luis) | abierto (conocido) |

**Actualización del 26-nov:** S1, S3, S4, S7 y S12 quedaron corregidos en #94; el resto de los hallazgos sigue abierto. S1 y S3 se comprobaron en PostgreSQL real con peticiones concurrentes (sección de pruebas de #94).

No se encontró ningún hallazgo de severidad alta: ningún rol entra donde no debe, ninguna respuesta pública lleva datos
del autor y no hay secretos en el historial.

### Matriz rol × endpoint probada en vivo

Cada celda es el código HTTP real (sin token / ciudadano / moderador / coordinador). Las rutas con id usaron un reporte o
cuenta nuevos en cada llamada. Los 401 llevaron `NO_AUTENTICADO` y los 403 `SIN_PERMISO`.

| Endpoint | Sin token | Ciudadano | Moderador | Coordinador |
|---|---|---|---|---|
| `GET /api/health`, `/reglas`, `/sectores`, `/colonias`, `/tipos-dano`, `/motivos-rechazo` | 200 | 200 | 200 | 200 |
| `GET /api/reportes`, `GET /api/reportes/{id}`, `GET /api/zona`, `GET /api/clima/aviso` | 200 | 200 | 200 | 200 |
| `POST /api/auth/refresh`, `GET /api/auth/yo` | 401 | 200 | 200 | 200 |
| `POST /api/reportes/baches`, `POST /api/reportes/encharcamientos` | 401 | 201 | 403 | 403 |
| `GET /api/reportes/cercanos`, `GET /api/mis-reportes` | 401 | 200 | 403 | 403 |
| `POST /api/reportes/{id}/confirmaciones` | 401 | 201 | 403 | 403 |
| `PUT /api/reportes/{id}` / `DELETE /api/reportes/{id}` (propio) | 401 | 200 / 204 | 403 | 403 |
| `GET /api/moderacion/bandeja`, `POST .../validar`, `POST .../rechazar` | 401 | 403 | 200 | **403** |
| `GET /api/moderacion/seguimiento`, `POST /api/reportes/{id}/estado` | 401 | 403 | 200 | 200 |
| `GET /api/usuarios`, `PUT /api/usuarios/{id}/rol`, `PUT /api/usuarios/{id}/suspension` | 401 | 403 | 403 | 200 |
| `GET /api/tablero` | 401 | 403 | 403 | 200 |
| `POST/PUT /api/sectores`, `POST/PUT/DELETE /api/colonias` | 401 | 403 | 403 | 201/200/204 |
| `GET /api/geo/buscar?q=` (vacío, sin salir a Nominatim) | 422 | 422 | 422 | 422 |

33 filas × 4 casos = 132 comprobaciones, todas como lo pide el contrato (sección 7). Registro y login se probaron aparte;
`GET /api/geo/inversa` no (ver S12). La matriz automática de `test_seguridad.py` más las de `test_admin_usuarios.py`,
`test_admin_catalogos.py` y `test_avance_reparacion.py` cubren todas las rutas de la API.

### Verificado sin problema

- **A01:** `usuario_actual` relee rol y `activo` en cada petición: una cuenta suspendida con token vigente recibe 403
  `CUENTA_SUSPENDIDA` (también al renovar y al entrar); un moderador degradado pierde la bandeja con el mismo token; un
  moderador suspendido que consulta una ruta pública se trata como público (no ve rechazados). El coordinador no usa
  bandeja/validar/rechazar. Un ciudadano no puede cambiarse el rol. Último coordinador: suspenderse o degradarse → 409
  `ULTIMO_COORDINADOR`; dos coordinadores que se degradan uno al otro a la vez dejan siempre uno activo.
- **IDOR:** B no edita ni borra el reporte de A (403); `mis-reportes` ignora `?autor_id=`; el autor no confirma lo suyo
  (403 `ES_TU_REPORTE`); 6 confirmaciones simultáneas de una persona → una sola 201 y cinco 409.
- **Rechazados:** `GET /api/reportes?estado=rechazado` sin sesión, con ciudadano o con token inválido → 0; con moderador →
  45. El detalle de un rechazado es 404 para el público y 200 para el coordinador; confirmar un rechazado → 404. Un
  parámetro `incluir_rechazados` en la URL no tiene efecto (lo decide el servidor).
- **Privacidad (RN-04):** se recorrió el JSON de consulta (activos, reparados, rechazados), detalle, zona, cercanos,
  bandeja, seguimiento, tablero y el 409 de duplicado: ninguna llave `autor`, `autor_id`, `usuario_id`, `correo`,
  `actor`, `actor_id`, `password*`, `motivo_texto`. El historial público no trae quién hizo el cambio. `GET /api/usuarios`
  y `/auth/yo` no traen el hash.
- **Entradas:** `hasta=9999-12-31` y `desde=0001-01-01` → 422 en consulta y tablero; `pagina=10001`, `tam=101`,
  `pagina=0` → 422; `q` con `' OR 1=1 --`, `%`, `_` y `\` → 200 con 0 resultados (parámetros y `autoescape`); `q` de 101
  caracteres → 422; `lat/lon` `nan` o `inf` (también `NaN` dentro del JSON) → 422; descripción y comentario enormes → 422.
  Campos extra se ignoran: un registro con `"rol": "coordinador"` nace ciudadano; un bache con `estado`, `autor_id`,
  `severidad`, `folio`, `creado_en` y `confirmaciones` inventados los ignora; un cambio de rol con `activo` extra solo cambia
  el rol; rol inválido → 422. Enumeraciones con `Literal`.
- **A07:** JWT con algoritmo fijo y `exp`/`sub` obligatorios: vencido, sin `exp`, sin `sub`, otra clave, `alg: none`,
  HS512, firma alterada, `sub` no numérico o de un usuario inexistente → 401. Mensaje y código idénticos para correo
  inexistente y contraseña mala, con el mismo tiempo de respuesta (mediana 0.19 s en los dos). Contraseña de 74 bytes →
  422 al registrar; login con 200 bytes → 401 (no 500). Correo sin distinguir mayúsculas (índice único sobre
  `lower(correo)`). En producción no arranca con la clave de ejemplo ni con una de menos de 32 caracteres (revisión de
  `core/config.py`, no ejecutado en modo producción).
- **A02/A05:** CORS solo para `CORS_ORIGINS`: un origen ajeno no recibe `Access-Control-Allow-Origin` (ni en el preflight
  ni en un GET) y no se envían credenciales. Cabeceras `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`
  y `Cache-Control: no-store`; HSTS solo en producción. 404, 405 y JSON inválido responden con la forma del contrato y sin
  traza; los 500 solo dicen `ERROR_INTERNO`. Dockerfiles sin root (`useradd` + `USER app`; nginx `unprivileged`); `.env`
  fuera de Git y de las imágenes (`.dockerignore`). `render.yaml` sin secretos (`generateValue` y `sync: false`).
- **Workflows:** `permissions: contents: read` en los dos; sin `pull_request_target`; ninguna expresión `${{ github.event... }}`
  dentro de `run:`. `despliegue.yml` solo corre en `push` a `main` o a mano, pasa el Deploy Hook por variable de entorno
  (GitHub lo enmascara) y no lo imprime.
- **Lógica:** cambios de estado con `with_for_update` (`obtener_reporte_para_cambiar`), folios con bloqueo de fila,
  confirmaciones con restricción única, `expirar_vencidos` al inicio de cada lectura, historial solo de inserción (ORM y
  trigger de PostgreSQL de la migración 0001; revisado en código).

### Lo que NO se pudo verificar

- Nada de los sitios desplegados (Vercel, Render, Neon): cabeceras reales de Vercel (HSTS), variables de Render, la CSP en
  el navegador. Por regla, todo fue local.
- Dependencias de Python con una herramienta de vulnerabilidades (no hay `pip-audit`); solo revisión manual.
- El trigger del historial con un `UPDATE`/`DELETE` directo en SQL (se leyó, no se ejecutó) y el arranque con
  `ENTORNO=produccion`.
- `GET /api/geo/inversa` y `GET /api/geo/buscar` con texto, porque salen a Nominatim.
- Las carreras de dos «ya no hay agua» simultáneos sobre el mismo encharcamiento (por lectura de código podrían no cerrarlo
  o escribir dos filas «historico»; no se reprodujo).
- El frontend en el navegador (XSS real, manejo del token); solo se buscaron `dangerouslySetInnerHTML`, `innerHTML` y
  `eval` en `frontend/src` (no hay).
