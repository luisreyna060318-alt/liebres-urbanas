# Liebre Urbana — Contrato de la API

Formas exactas de las peticiones y respuestas. Es el acuerdo que deja construir el backend y el frontend al mismo tiempo.
Complementa a [DISENO_TECNICO.md](DISENO_TECNICO.md) (que lista los endpoints y las reglas). Si algo cambia, se cambia aquí en un PR
pequeño. Los endpoints que construye Carlos (consulta, moderación, administración, tablero, clima) definen su forma en su PR y la
agregan a este archivo; las formas de `ReportePublico` y de la paginación ya son comunes.

## 1. Convenciones

- Prefijo `/api`. Cuerpo y respuesta en JSON UTF-8. Textos en español de México.
- Autenticación: `Authorization: Bearer <access_token>`.
- Fechas y horas: ISO 8601 en UTC con `Z` (`"2026-11-24T21:05:00Z"`). El frontend las muestra con
  `Intl.DateTimeFormat` y `timeZone: "America/Ciudad_Juarez"`. `fecha_reparacion` es solo fecha (`"2026-11-20"`).
- Coordenadas: `lat` y `lon` como números decimales (grados).
- Paginación: `?pagina=1&tam=20`. Respuesta `{"items": [...], "total": 137, "pagina": 1, "tam": 20}`.
- Nombres de campos en `snake_case` y sin acentos ni eñes (`tamano`, `senalizado`).

### Errores

Todo error del servidor tiene esta forma:

```json
{ "detail": "Mensaje para mostrar a la persona", "codigo": "ETIQUETA_ESTABLE", "campos": { "password": "Mensaje del campo" } }
```

`campos` solo aparece en los errores de validación (422). Códigos HTTP usados: 400, 401, 403, 404, 409, 422, 429, 503
(y 405/500 para errores genéricos: método no permitido y error inesperado, que nunca muestra detalles técnicos).

| HTTP | `codigo` | Cuándo |
|---|---|---|
| 401 | `NO_AUTENTICADO` | Falta el token, está vencido o es inválido |
| 401 | `CREDENCIALES` | Correo o contraseña incorrectos (mismo mensaje para los dos casos) |
| 403 | `SIN_PERMISO` | El rol no puede usar el endpoint, o no es el autor |
| 403 | `CUENTA_SUSPENDIDA` | La cuenta está suspendida |
| 403 | `ES_TU_REPORTE` | Intento de confirmar el reporte propio |
| 404 | `NO_ENCONTRADO` | El recurso no existe (o no es visible para esa persona) |
| 409 | `CORREO_REGISTRADO` | El correo ya existe |
| 409 | `POSIBLE_DUPLICADO` | Hay un reporte cercano y no se envió `forzar: true` (incluye `duplicados`) |
| 409 | `YA_CONFIRMADO` | La persona ya respondió sobre ese reporte |
| 409 | `REPORTE_NO_EDITABLE` | El reporte ya no está en Recibido |
| 409 | `TRANSICION_INVALIDA` | Salto de estado no permitido por RN-05 |
| 422 | `VALIDACION` | Datos inválidos (con `campos`) |
| 422 | `FUERA_DEL_MUNICIPIO` | Las coordenadas están fuera de Juárez |
| 429 | `LIMITE_HORARIO` | Más de 10 reportes por hora |
| 503 | `SERVICIO_NO_DISPONIBLE` | Nominatim u otro servicio externo no responde (o la base de datos, en `/api/health`) |
| 405 | `METODO_NO_PERMITIDO` | El método HTTP no existe en esa ruta |
| 500 | `ERROR_INTERNO` | Error inesperado del servidor |

## 2. Valores permitidos (enumeraciones)

| Campo | Valores |
|---|---|
| `rol` | `ciudadano`, `moderador`, `coordinador` |
| `categoria` | `bache`, `encharcamiento` |
| `tipo_dano_codigo` | `bache`, `hundimiento`, `grieta`, `alcantarilla_sin_tapa` |
| `tamano` | `chico` (< 30 cm), `mediano` (30 cm a 1 m), `grande` (> 1 m) |
| `profundidad` | `baja`, `media`, `alta` |
| `carril` | `orilla`, `izquierdo`, `derecho`, `varios` |
| `severidad` | `baja`, `media`, `alta` (la calcula el servidor) |
| `nivel_agua` | `a_un_lado`, `cubre_carril`, `media_llanta`, `intransitable` |
| `estado` (bache) | `recibido`, `validado`, `en_reparacion`, `reparado`, `rechazado` |
| `estado` (encharcamiento) | `activo`, `historico`, `rechazado` |
| `tipo` de confirmación | `confirma` (bache), `sigue` y `ya_no_hay` (encharcamiento) |

## 3. Cuenta y sesión

`UsuarioPublico` = `{ "id": 7, "nombre": "Ana Pérez", "correo": "ana@ejemplo.test", "rol": "ciudadano" }`
(solo se devuelve a la propia persona o al coordinador; **nunca** el hash).

`SesionRespuesta` = `{ "access_token": "...", "token_type": "bearer", "expira_en_min": 30, "usuario": UsuarioPublico }`

| Endpoint | Entrada | Salida |
|---|---|---|
| `POST /api/auth/registro` | `{ "nombre", "correo", "password", "acepta_privacidad": true }` | 201 `SesionRespuesta` (la persona queda dentro) |
| `POST /api/auth/login` | `{ "correo", "password" }` | 200 `SesionRespuesta` |
| `POST /api/auth/refresh` | (token vigente) | 200 `SesionRespuesta` con un token nuevo de 30 min |
| `GET /api/auth/yo` | (token) | 200 `UsuarioPublico` |

Validación del registro: `nombre` 2 a 80 caracteres; `correo` válido; `password` de 8 caracteres o más con letras y números;
`acepta_privacidad` debe ser `true`. Cada error de campo va en `campos`, con el nombre del campo de la entrada.

## 4. Reglas y catálogos

`GET /api/reglas` →

```json
{
  "radio_duplicado_bache_m": 30, "radio_duplicado_encharcamiento_m": 50, "vigencia_encharcamiento_horas": 6,
  "desmentidos_para_cerrar": 3, "radio_zona_km": 1, "max_reportes_por_hora": 10, "descripcion_max": 500,
  "password_min": 8, "inactividad_min": 30, "tam_pagina_consulta": 20, "tam_pagina_mis_reportes": 10,
  "umbral_lluvia_pct": 30, "zona_horaria": "America/Ciudad_Juarez"
}
```

| Endpoint | Salida |
|---|---|
| `GET /api/health` | `{ "estado": "ok", "base_de_datos": "ok" }` (503 `SERVICIO_NO_DISPONIBLE` si la base no responde) |
| `GET /api/sectores` | `[ { "id": 1, "nombre": "Centro" } ]` (orden alfabético) |
| `GET /api/colonias?q=&sector_id=&solo_activas=true&pagina=1&tam=10` | Paginación de `{ "id", "nombre", "sector": { "id", "nombre" }, "activa", "lat", "lon" }`, en orden alfabético. `tam` vale 10 por omisión (catálogos) y acepta hasta 500 para llenar listas |
| `GET /api/tipos-dano` | `[ { "id", "codigo", "nombre" } ]` (solo los activos) |
| `GET /api/motivos-rechazo` | `[ { "id", "codigo", "nombre", "pide_explicacion" } ]` (solo los activos) |

## 5. Ubicación (Nominatim)

| Endpoint | Salida |
|---|---|
| `GET /api/geo/buscar?q=Av. Tecnológico 1340` | `{ "resultados": [ GeoResultado ] }` (hasta 5, ya restringidos a Ciudad Juárez) |
| `GET /api/geo/inversa?lat=31.7&lon=-106.4` | `GeoResultado` |

`GeoResultado` = `{ "etiqueta": "texto completo", "lat": 31.7, "lon": -106.4, "calle": "Av. Tecnológico", "colonia_id": 12 | null, "colonia_nombre": "Partido Escobedo" | null, "dentro_del_municipio": true }`.
Si no hay coincidencias, `resultados` está vacío (no es un error). Si Nominatim falla: 503 `SERVICIO_NO_DISPONIBLE`.
`colonia_id` es `null` cuando el nombre devuelto no coincide con el catálogo; en ese caso la persona elige la colonia en una lista.
`calle` también puede ser `null` (Nominatim no siempre la trae). `q` necesita al menos 3 caracteres (422 `VALIDACION`
con `campos.q`). En `inversa` el resultado conserva las coordenadas enviadas; si Nominatim no encuentra un lugar en ese punto,
responde 200 con `etiqueta` = `"lat, lon"` y `calle`, `colonia_id` y `colonia_nombre` en `null` (la persona los captura a mano).
`dentro_del_municipio` se calcula sin internet con el rectángulo `MUNICIPIO_BBOX` de `backend/app/core/reglas.py` (RN-01).

## 6. Reportes

### 6.1 `ReportePublico`

Lo que ve cualquier persona. **Nunca** incluye al autor (nombre, correo ni id).

```json
{
  "id": 345, "folio": "BCH-2026-000123", "categoria": "bache",
  "tipo_dano": { "codigo": "bache", "nombre": "Bache" },
  "calle": "Av. Tecnológico", "colonia": { "id": 12, "nombre": "Partido Escobedo" },
  "lat": 31.7001, "lon": -106.4302, "descripcion": "Hueco grande junto al semáforo",
  "severidad": "alta", "tamano": "grande", "profundidad": "media", "carril": "derecho", "senalizado": null,
  "nivel_agua": null, "hay_riesgo": null,
  "estado": "recibido", "sin_validar": true, "confirmaciones": 2,
  "creado_en": "2026-11-24T21:05:00Z", "vigente_hasta": null, "fecha_reparacion": null,
  "antiguedad_dias": 0
}
```

- Los campos propios de la otra categoría vienen en `null` (por ejemplo `nivel_agua` en un bache, y `tipo_dano` en un encharcamiento).
- `sin_validar` es `true` solo para baches en `recibido` (RN-09: se muestran con la etiqueta "Sin validar").
- `antiguedad_dias`: días desde `creado_en` hasta hoy, o hasta `fecha_reparacion` en un bache reparado (RN-10).
- Los reportes `rechazado` no se devuelven en consultas públicas.

`ReporteMio` = `ReportePublico` + `{ "puede_editar": true, "motivo_rechazo": { "nombre": "Duplicado", "texto": "..." } | null }`
(solo para el autor; `puede_editar` es `true` únicamente en `recibido`).

`ReporteDetalle` = `ReportePublico` + `{ "longevidad_dias": 5, "ultima_actividad": "2026-11-25T10:00:00Z", "historial": [ CambioEstado ] }`
con `CambioEstado` = `{ "estado_anterior": "recibido" | null, "estado_nuevo": "validado", "comentario": "..." | null, "creado_en": "..." }`
del más reciente al más antiguo. El historial público **no** incluye quién hizo el cambio.

### 6.2 Crear un bache — `POST /api/reportes/baches` (rol ciudadano)

```json
{
  "tipo_dano_codigo": "bache", "lat": 31.7001, "lon": -106.4302, "calle": "Av. Tecnológico", "colonia_id": 12,
  "descripcion": "Hueco grande junto al semáforo",
  "tamano": "grande", "profundidad": "media", "carril": "derecho",
  "senalizado": null, "forzar": false
}
```

- `tipo_dano_codigo = "bache"` exige `tamano`, `profundidad` y `carril`. `hundimiento` y `grieta` exigen `tamano` y `carril`.
  `alcantarilla_sin_tapa` exige `senalizado` (booleano) y la severidad queda en `alta` sin que la persona la elija.
- `descripcion` es opcional (hasta 500 caracteres). `calle` y `colonia_id` se pueden corregir antes de enviar.
- Si existe un bache abierto a 30 m o menos y `forzar` no es `true` → **409** `POSIBLE_DUPLICADO` con
  `"duplicados": [ ReportePublico + { "distancia_m": 12 } ]`. Con `forzar: true` se crea uno nuevo (HU-02.3 CA4).
- 201 → `ReporteMio` con folio, `creado_en` asignado por el servidor y estado `recibido`. Si la entrada trae `creado_en`,
  `estado`, `severidad` o `confirmaciones`, se ignoran. `senalizado` solo se guarda en `alcantarilla_sin_tapa`; en
  `hundimiento` y `grieta` `profundidad` es opcional (si llega, cuenta para la severidad).
- Errores en este orden: 422 `VALIDACION` (con `campos`), 422 `FUERA_DEL_MUNICIPIO`, 429 `LIMITE_HORARIO`, 409 `POSIBLE_DUPLICADO`.

### 6.3 Crear un encharcamiento — `POST /api/reportes/encharcamientos` (rol ciudadano)

```json
{ "lat": 31.7001, "lon": -106.4302, "calle": "Av. Tecnológico", "colonia_id": 12, "descripcion": "",
  "nivel_agua": "intransitable", "hay_riesgo": true, "forzar": false }
```

- `nivel_agua = "intransitable"` exige `hay_riesgo` (¿hay vehículos varados o personas en riesgo?).
- Si hay un encharcamiento activo a 50 m o menos y no se envió `forzar: true` → 409 `POSIBLE_DUPLICADO`.
- 201 → `ReporteMio` en estado `activo` con `vigente_hasta` = ahora + 6 h (se publica de inmediato, RN-06).

### 6.4 Reportes cercanos — `GET /api/reportes/cercanos?categoria=bache&lat=..&lon=..` (rol ciudadano)

`[ ReportePublico + { "distancia_m": 12 } ]`, ordenados por distancia, con el radio de cada categoría (30 m o 50 m).

### 6.5 Confirmar — `POST /api/reportes/{id}/confirmaciones` (rol ciudadano)

Entrada `{ "tipo": "confirma" | "sigue" | "ya_no_hay" }`. Salida 201 `ReportePublico` actualizado.

- `confirma` solo en baches abiertos; suma 1 a `confirmaciones`.
- `sigue` solo en encharcamientos activos; suma 6 h a la vigencia **desde ese momento**.
- `ya_no_hay` solo en encharcamientos activos; con el tercer desmentido de personas distintas el reporte pasa a `historico`.
- Una persona responde una sola vez por reporte (409 `YA_CONFIRMADO`); no puede responder el suyo (403 `ES_TU_REPORTE`).
- Reporte inexistente o rechazado → 404 `NO_ENCONTRADO`. Tipo que no corresponde a la categoría → 422 `VALIDACION`
  (`campos.tipo`). Reporte ya cerrado (bache `reparado`, encharcamiento `historico` o vencido) → 409 `TRANSICION_INVALIDA`.
- `ya_no_hay` no suma a `confirmaciones`; `sigue` y `confirma` sí. Cada respuesta se guarda con su fecha y hora.

### 6.6 Mis reportes

| Endpoint | Entrada | Salida |
|---|---|---|
| `GET /api/mis-reportes?pagina=1` | — | Paginación (10 por página) de `ReporteMio`, del más reciente al más antiguo |
| `PUT /api/reportes/{id}` | Los mismos campos editables del alta (sin `forzar`) | 200 `ReporteMio`; 409 `REPORTE_NO_EDITABLE` si ya no está en `recibido` |
| `DELETE /api/reportes/{id}` | — | 204; 409 `REPORTE_NO_EDITABLE` |

Solo el autor puede editar o eliminar (403 `SIN_PERMISO` para otra persona).
Orden de las revisiones: 404 si no existe → 403 si no es el autor → 409 si ya no está en `recibido`. El `PUT` recibe los
campos de un **bache** (un encharcamiento nace `activo`, así que nunca es editable ni se puede eliminar: 409). Al eliminar se
borran también su historial y sus confirmaciones.

### 6.8 Vigencia de encharcamientos

No hay tareas programadas: `services/encharcamientos.expirar_vencidos(db)` pasa a `historico` los activos con `vigente_hasta`
vencido (historial con actor `null` = sistema). Lo llaman al inicio el alta de encharcamientos, `cercanos`, `confirmaciones` y
`mis-reportes`; los endpoints de consulta pública, detalle, zona y tablero también deben llamarlo antes de leer.

### 6.7 Consulta pública (la construye Carlos; la forma ya queda fijada)

`GET /api/reportes?categoria=&estado=&colonia_id=&severidad=&desde=&hasta=&q=&pagina=1&tam=20` → paginación de `ReportePublico`.
`GET /api/reportes/{id}` → `ReporteDetalle`. Por omisión solo "activos": baches abiertos y encharcamientos activos.

## 7. Qué pide cada endpoint de rol

| Rol | Puede |
|---|---|
| Público | Consultar reportes, detalle, zona, catálogos, reglas, clima, geocodificación |
| `ciudadano` | Todo lo público + crear, confirmar, ver, editar y borrar sus reportes |
| `moderador` | Todo lo público + bandeja, validar, rechazar y registrar avance |
| `coordinador` | Todo lo del moderador + catálogos, usuarios y roles, tablero |

Un rol por persona: moderador y coordinador **no** crean ni confirman reportes (403 `SIN_PERMISO`).

## 8. Consulta pública (C3 y C4)

Completa la sección 6.7. Los dos endpoints son **públicos**: no exigen sesión y nunca incluyen al autor (RN-04).
Aceptan un token **opcional**: si es válido y la cuenta es de moderador o coordinador, se pueden ver los rechazados.
Un token vencido, inválido o de una cuenta suspendida se trata como público (**no** responde 401).
Ambos llaman antes a `expirar_vencidos(db)`, así un encharcamiento vencido ya aparece como `historico`.

### 8.1 Consultar reportes — `GET /api/reportes` (HU-04.1 y HU-04.2)

| Parámetro | Valores | Notas |
|---|---|---|
| `categoria` | `bache`, `encharcamiento` | |
| `estado` | cualquiera de la sección 2 | Sin valor: solo **activos** (baches `recibido`, `validado`, `en_reparacion` y encharcamientos `activo`) |
| `colonia_id` | entero ≥ 1 | |
| `severidad` | `baja`, `media`, `alta` | Solo baches (los encharcamientos no tienen severidad) |
| `desde`, `hasta` | `AAAA-MM-DD` | Días del calendario de **Ciudad Juárez**, los dos incluidos, sobre `creado_en` |
| `q` | texto, hasta 100 caracteres | Parte de la calle o del folio, sin distinguir mayúsculas; `%` y `_` se buscan tal cual |
| `pagina`, `tam` | `pagina` ≥ 1; `tam` de 1 a 100 | `tam` vale 20 por omisión |

- 200 → `Pagina[ReportePublico]` (sección 6.1), del más reciente al más antiguo (`creado_en` desc, `id` desc). `total`
  cuenta todos los resultados del filtro; una página fuera de rango devuelve `items: []` con el mismo `total`.
- Los filtros se combinan con "y". `estado=rechazado` sin sesión de moderación responde 200 con `items: []`.
- 422 `VALIDACION` con `campos` por parámetro: fecha mal escrita, `desde` posterior a `hasta` (`campos.hasta`),
  valores fuera de las enumeraciones, `pagina`/`tam` fuera de rango, `q` demasiado largo.
- El filtrado vive en una sola función, `services/consulta.consulta_reportes(FiltroReportes)`, que también acepta
  `sector_id` (todavía no expuesto aquí). El tablero (HU-07.1) debe usarla para que sus cifras coincidan con la consulta.

## 14. Tablero de indicadores (C10)

### 14.1 `GET /api/tablero?desde=&hasta=&sector_id=` (HU-07.1, solo `coordinador`)

| Parámetro | Valores | Notas |
|---|---|---|
| `desde`, `hasta` | `AAAA-MM-DD` | Días del calendario de **Ciudad Juárez**, los dos incluidos, sobre `creado_en` (igual que la sección 8.1) |
| `sector_id` | entero ≥ 1 | Solo los reportes de las colonias de ese sector |

**Una sola función de filtrado.** Todas las cifras salen de `services/consulta.consulta_reportes(FiltroReportes)` con
`desde`, `hasta` y `sector_id`; el tablero solo cuenta y agrupa su resultado. Por eso cada conteo por estado coincide
con `GET /api/reportes?categoria=..&estado=..&desde=..&hasta=..` (HU-07.1 CA5). Antes de leer llama a `expirar_vencidos(db)`.

**Qué cuenta.** Todos los estados salvo `rechazado`: baches `recibido`, `validado`, `en_reparacion`, `reparado` y
encharcamientos `activo` e `historico` (los históricos **sí** cuentan, HU-03.2 CA3). Los rechazados van aparte en
`totales.rechazados` y no suman en `total`. "Abierto" = bache en `recibido`, `validado` o `en_reparacion`.

```json
{
  "filtro": { "desde": "2026-09-01", "hasta": null, "sector_id": 3 },
  "totales": {
    "total": 120, "bache": 90, "encharcamiento": 30, "rechazados": 4,
    "por_estado": [
      { "categoria": "bache", "estado": "recibido", "total": 20 },
      { "categoria": "bache", "estado": "validado", "total": 30 },
      { "categoria": "bache", "estado": "en_reparacion", "total": 10 },
      { "categoria": "bache", "estado": "reparado", "total": 30 },
      { "categoria": "encharcamiento", "estado": "activo", "total": 5 },
      { "categoria": "encharcamiento", "estado": "historico", "total": 25 }
    ]
  },
  "top_colonias": [ { "colonia": { "id": 12, "nombre": "Partido Escobedo" }, "abiertos": 8 } ],
  "tiempo_promedio_reparacion_dias": 6.4,
  "reparados_medidos": 28,
  "por_semana": [ { "inicio": "2026-09-07", "total": 0 }, { "inicio": "2026-09-14", "total": 9 } ],
  "mas_longevos": [
    { "id": 345, "folio": "BCH-2026-000123", "calle": "Av. Tecnológico",
      "colonia": { "id": 12, "nombre": "Partido Escobedo" }, "estado": "validado", "antiguedad_dias": 41 }
  ],
  "longevidad_por_colonia": [ { "colonia": { "id": 12, "nombre": "Partido Escobedo" }, "abiertos": 8, "promedio_dias": 17.3 } ]
}
```

- `por_estado` trae siempre los 6 pares (categoría, estado), en ese orden, aunque valgan 0.
- `top_colonias`: hasta 10 colonias con más baches abiertos; empate → por nombre (alfabético) y luego por `id`.
- `tiempo_promedio_reparacion_dias`: promedio, con un decimal, de los días entre la fila del historial que pasó el bache a
  `validado` y la que lo pasó a `reparado` (diferencia de fecha y hora, en días con fracción). Solo baches `reparado`
  dentro del filtro que tengan las dos filas; `reparados_medidos` dice cuántos. `null` si no hay ninguno.
- `por_semana`: siempre **12** semanas de lunes a domingo (hora de Juárez), de la más antigua a la más reciente, con ceros.
  La serie termina en la semana de `hasta` o, si no se envió, en la semana actual; `desde` **no** recorta la serie, pero
  sí el conteo (las semanas anteriores a `desde` quedan en 0). Respeta `sector_id`.
- `mas_longevos`: los 10 baches abiertos con `creado_en` más antiguo (empate por `id`). `antiguedad_dias` sigue RN-10
  (días desde `creado_en`, en fecha de Juárez, hasta hoy).
- `longevidad_por_colonia`: todas las colonias con baches abiertos, con su antigüedad promedio (RN-10, un decimal),
  de la más alta a la más baja (empate por nombre).
- Sin autor ni datos personales en ninguna parte (RN-04). Los valores 10 y 12 viven en `core/reglas.py`
  (`TABLERO_TOP_COLONIAS`, `TABLERO_MAS_LONGEVOS`, `TABLERO_SEMANAS`).
- Errores: 401 `NO_AUTENTICADO` sin sesión; 403 `SIN_PERMISO` para ciudadano y moderador; 422 `VALIDACION` con
  `campos.hasta` si `desde` > `hasta`, `campos.sector_id` si el sector no existe o es < 1, y `campos.desde`/`campos.hasta`
  si la fecha está mal escrita.
