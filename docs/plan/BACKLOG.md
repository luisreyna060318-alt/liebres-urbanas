# Liebre Urbana — Backlog

Fuente: *Requerimientos del cliente* (5 de noviembre de 2026). Cada historia conserva su ID (HU-xx.x) y sus criterios (CA1, CA2…)
para usarlos en issues, PRs y pruebas. Este archivo es la versión de trabajo; en GitHub el backlog está en los issues #38 a #71 (no se creó un tablero de Projects).

Leyenda: **I** indispensable, **D** deseable. **P0** se entrega sí o sí, **P1** si P0 está desplegado, **P2** trabajo futuro.
**L** = Luis, **C** = Carlos. Los PRs se describen en `PLAN_DE_TRABAJO.md` (sección 5). El reparto de P1 se confirma el miércoles a las 20:00.

## Resumen de cobertura

| Nivel | Historias | Luis | Carlos |
|---|---|---|---|
| P0 (I) | 20 | 10 | 10 |
| P1 (D) | 8 | 2 | 6 |
| P2 (D) | 6 | — | — |
| **Total** | **34** | | |

La materia exige un backlog con al menos 15 historias: aquí hay 34 con criterios de aceptación. Al 26-nov están implementadas las 20 indispensables (P0).

---

## Historias de usuario

### E1. Cuentas y acceso

| ID | Historia | Pri. | Nivel | Dueño | PR | Cómo se resuelve (puntos de cuidado) |
|---|---|---|---|---|---|---|
| HU-01.1 | Crear una cuenta | I | P0 | L | L1, L2 | Rol Ciudadano por defecto; correo único sin importar mayúsculas (CA2); contraseña ≥ 8 con letras y números, error junto al campo sin perder lo capturado (CA3); casilla de aviso de privacidad obligatoria en cliente y servidor (CA4) |
| HU-01.2 | Iniciar y cerrar sesión | I | P0 | L | L1, L2 | Mensaje único para correo o contraseña incorrectos (CA2); al cerrar sesión se borra el token y las rutas privadas piden login (CA3); **30 min de inactividad** (CA4, documentado) con renovación del token mientras hay actividad |
| HU-01.3 | Hacer solo lo que mi rol permite | I | P0 | L | L2, L11 | Dependencia `require_role` en cada endpoint protegido; el menú oculta opciones, pero la defensa real es el servidor (403) (CA2); solo el autor edita o borra su reporte (CA3); matriz de pruebas rol × endpoint |
| HU-01.4 | Elegir mis colonias de interés | D | P1 | L | P1 | Tabla `usuario_colonias` (relación N:M); la consulta ordena primero esas colonias (CA2) |

### E2. Reporte de baches

| ID | Historia | Pri. | Nivel | Dueño | PR | Cómo se resuelve |
|---|---|---|---|---|---|---|
| HU-02.1 | Reportar un bache | I | P0 | L | L6, L12 | Dirección o ubicación del dispositivo → coordenadas, calle y colonia, corregibles (CA1); fuera del municipio → 422 con mensaje (CA2); folio `BCH-2026-000123`, fecha asignada por el servidor y estado Recibido (CA3); si falla la conexión no se pierde lo capturado (CA4) |
| HU-02.2 | Describir el daño según su tipo | I | P0 | L | L7, L12 | Campos distintos por tipo (bache, hundimiento, grieta, alcantarilla sin tapa); tamaño, profundidad y carril para bache; alcantarilla = severidad Alta automática + pregunta de señalización; descripción ≤ 500 caracteres validada también en el servidor (CA4) |
| HU-02.3 | Evitar reportes duplicados | I | P0 | L | L8, L12 | Reportes abiertos a ≤ 30 m (fórmula de Haversine); confirmar suma 1 sin folio nuevo; una confirmación por persona (restricción única en BD); "reportar de todos modos" crea un reporte nuevo |
| HU-02.4 | Adjuntar fotografías | D | P2 | — | — | Pendiente: requiere almacenamiento persistente (el disco gratuito de Render se borra) |
| HU-02.5 | Consultar y corregir mis reportes | I | P0 | L | L9, L13 | Paginación de 10 en 10; editar o eliminar **solo** en Recibido, y el servidor lo valida (CA3); mensaje que invita a crear el primero (CA4) |

### E3. Reporte de encharcamientos

| ID | Historia | Pri. | Nivel | Dueño | PR | Cómo se resuelve |
|---|---|---|---|---|---|---|
| HU-03.1 | Reportar un encharcamiento | I | P0 | L | L10, L14 | Niveles: a un lado de la calle, cubre un carril, a media llanta, intransitable; "Intransitable" exige responder si hay vehículos varados o personas en riesgo (CA3); folio `ENC-2026-000045`; si hay uno vigente a ≤ 50 m se ofrece confirmarlo (CA4); se publica como Activo de inmediato (RN-06) |
| HU-03.2 | Vigencia automática | I | P0 | L | L10 | Columna `vigente_hasta` (6 h); cada confirmación "sigue ahí" suma 6 h desde ese momento (CA2); **sin tareas programadas**: antes de cada consulta se pasan a Histórico los vencidos y se anota en el historial como "sistema"; los Históricos sí cuentan en los indicadores (CA3) |
| HU-03.3 | Confirmar o desmentir | I | P0 | L | L10, L14 | "Sigue ahí" o "Ya no hay agua" con fecha y hora; una respuesta por persona; 3 desmentidos distintos → Histórico (CA3); el autor no puede confirmar el suyo (CA4) |
| HU-03.4 | Puntos recurrentes | D | P1 | C | P1 | ≥ 3 días distintos del año dentro de 50 m; el coordinador ve cuántos días y la fecha más reciente |

### E4. Consulta ciudadana

| ID | Historia | Pri. | Nivel | Dueño | PR | Cómo se resuelve |
|---|---|---|---|---|---|---|
| HU-04.1 | Consultar reportes activos sin cuenta | I | P0 | C | C3 | Endpoint público sin datos personales (esquema de salida sin autor); baches y encharcamientos distinguidos por **texto e ícono**, no solo por color (CA3); los rechazados no se muestran (CA4) |
| HU-04.2 | Buscar y filtrar reportes | I | P0 | C | C3 | Filtros combinados (tipo, estado, colonia, severidad, fechas) y búsqueda por calle o folio; 20 por página con el total; mensaje y botón "Limpiar filtros". **Una sola función de consulta** que también usa el tablero (para que coincidan, HU-07.1 CA5) |
| HU-04.3 | ¿Cómo está mi zona? | I | P0 | C | C5 | Radio de 1 km, ordenado por distancia, con la distancia; Intransitable al inicio y resaltado; dirección no encontrada → mensaje y reintento |
| HU-04.4 | Ver el detalle y la historia de un reporte | I | P0 | C | C4 | Folio, tipo, ubicación, datos del daño, confirmaciones y estado; cambios del más reciente al más antiguo con comentario público; en baches: fecha del reporte original, longevidad en días y fecha de la confirmación más reciente |
| HU-04.5 | Ver los reportes en un mapa | D | P1 | C | P1 | Leaflet con mosaicos de OpenStreetMap; usa los mismos filtros que HU-04.2 |
| HU-04.6 | Revisar mi trayecto | D | P2 | — | — | Pendiente: requiere un servicio de rutas |

### E5. Validación y seguimiento

| ID | Historia | Pri. | Nivel | Dueño | PR | Cómo se resuelve |
|---|---|---|---|---|---|---|
| HU-05.1 | Validar o rechazar reportes nuevos | I | P0 | C | C6 | Bandeja de Recibidos del más antiguo al más reciente, filtros por colonia y tipo; validar queda en el historial con nombre, fecha y hora; rechazar exige motivo (otro → explicación obligatoria); el autor ve el motivo |
| HU-05.2 | Registrar el avance de una reparación | I | P0 | C | C7 | Máquina de estados de RN-05 (cualquier otro salto → 409); Reparado exige fecha no futura ni anterior al reporte; comentario público; el historial **no se puede modificar ni borrar** (sin ruta, error en la capa de datos y trigger en PostgreSQL) |
| HU-05.3 | Fusionar reportes duplicados | D | P2 | — | — | Pendiente |
| HU-05.4 | Asignar baches a una cuadrilla | D | P2 | — | — | Pendiente (agrega la entidad cuadrilla y el estado Programado) |
| HU-05.5 | Actualizar baches asignados desde la autoridad | D | P2 | — | — | Pendiente (agrega el rol enlace municipal) |

### E6. Administración

| ID | Historia | Pri. | Nivel | Dueño | PR | Cómo se resuelve |
|---|---|---|---|---|---|---|
| HU-06.1 | Administrar colonias y sectores | I | P0 | C | C8 | CRUD con búsqueda y paginación; con reportes solo se puede desactivar (409 al borrar); nombre único por sector (CA3) |
| HU-06.2 | Administrar usuarios y roles | I | P0 | C | C9 | Búsqueda por nombre o correo, filtro por rol, paginación; el rol y el estado de la cuenta se leen de la base **en cada petición**, así el cambio surte efecto en la siguiente acción (CA2); suspender impide entrar y conserva los reportes; no se puede quitar ni suspender al último coordinador |
| HU-06.3 | Tipos de daño y motivos de rechazo | D | P1 | C | P1 | Tablas de catálogo con campo `activo`; los reportes anteriores conservan lo que tenían |

### E7. Indicadores

| ID | Historia | Pri. | Nivel | Dueño | PR | Cómo se resuelve |
|---|---|---|---|---|---|---|
| HU-07.1 | Tablero de indicadores | I | P0 | C | C10 | Totales por tipo y estado; top 10 colonias con más baches abiertos; tiempo promedio de reparación (Validado → Reparado); reportes por semana en 12 semanas (gráfica SVG propia, sin librería); 10 baches más longevos y longevidad promedio por colonia; filtros por fecha y sector que **coinciden con HU-04.2** |
| HU-07.2 | Resumen público por colonia | D | P1 | C | P1 | Abiertos, reparados y tiempo promedio por colonia, sin datos personales |
| HU-07.3 | Exportar para la autoridad | D | P1 | C | P1 | CSV que abre en una hoja de cálculo (con BOM UTF-8) y XML validado contra un XSD propio documentado; sin nombres ni correos |

### E8. Avisos

| ID | Historia | Pri. | Nivel | Dueño | PR | Cómo se resuelve |
|---|---|---|---|---|---|---|
| HU-08.1 | Aviso de lluvia | I | P0 | C | C11 | Open-Meteo (sin llave) para las próximas 12 h; el aviso aparece si la probabilidad máxima alcanza el umbral documentado (30 %) y enlaza a HU-04.3; sin lluvia no aparece (CA2); caché de 1 h (CA3); si el servicio falla, la plataforma sigue y muestra "Pronóstico no disponible" (CA4) |
| HU-08.2 | Avisos sobre mis reportes | D | P1 | L | P1 | Tabla `notificaciones` que se llena al cambiar el estado; contador de no leídos y marcar como leído |
| HU-08.3 | Encharcamientos nuevos sin recargar | D | P1 | C | P1 | Consulta periódica cada 20 s mientras la pantalla está abierta (≤ 30 s, CA1) |
| HU-08.4 | Instalar en el celular (PWA) | D | P2 | — | — | Pendiente |

---

## Requerimientos no funcionales

| ID | Requerimiento | Dueño | Cómo se cumple y se verifica |
|---|---|---|---|
| RNF-01 | 360 px a escritorio | C | CSS con Flexbox/Grid y 2 puntos de corte; capturas en móvil y escritorio |
| RNF-02 | Accesibilidad (WCAG 2.2 AA) | C | HTML semántico, `label`, contraste, foco visible, teclado; Lighthouse ≥ 90 y axe; la información no depende solo del color |
| RNF-03 | URL pública el día de la entrega | L | Vercel + Render + Neon; URL en el README |
| RNF-04 | Levantar todo en otra computadora en < 3 min | C | `docker compose up`; imágenes ya construidas; prueba cronometrada |
| RNF-05 | Contraseñas invisibles; roles aunque se salten las pantallas | L | bcrypt, el hash nunca sale en ninguna respuesta; pruebas 401/403 |
| RNF-06 | Consulta < 3 s con 500 reportes | C | Índices en la tabla de reportes; medición con los datos de demo |
| RNF-07 | Pruebas automatizadas de lo indispensable | ambos | `pytest` (meta ≥ 25 pruebas) y Vitest; CI en cada push y PR |
| RNF-08 | Español de México | ambos | Textos y mensajes de error en español; revisión final |
| RNF-09 | Datos de demo | L | ≥ 20 colonias reales con fuente citada, 500 reportes ficticios en 12 semanas, una cuenta por rol |

---

## Issues y tablero (se crean con autorización de Luis)

1. **Issue #1 — Propuesta del proyecto** (lo pide la materia como primer issue): texto al final de este archivo.
2. **34 issues de historias**: título `HU-02.1 Reportar un bache`, cuerpo con la historia y sus CA copiados, etiquetas `epica:E2`, `prioridad:I`, `nivel:P0`, `dueño:luis`.
3. **8 issues transversales**: esqueleto API, modelo de datos, despliegue, CI/Docker, esqueleto React, semilla, pruebas y seguridad, documentación.
4. **Tablero "Liebre Urbana"** en GitHub Projects con columnas Pendiente, En curso, En revisión y Hecho; el tablero se mueve a lo largo del miércoles (la rúbrica evalúa que se actualice durante todo el proyecto).

---

## Anexo: texto del issue de propuesta

**Título:** Propuesta: Liebre Urbana, plataforma ciudadana de baches y encharcamientos

**Problema.** En Ciudad Juárez los vecinos reportan baches por redes sociales y mensajería; los reportes se pierden, se repiten y nadie
sabe si se atendieron. Cuando llueve, algunas calles se inundan y los conductores se enteran hasta que llegan.

**Usuarios.** Visitante (consulta sin cuenta), Ciudadano (reporta y confirma), Moderador (valida y registra el avance) y Coordinador
(administra usuarios y catálogos, y consulta indicadores).

**Solución.** Aplicación web (React + TypeScript, FastAPI y PostgreSQL) para reportar, consultar por zona y dar seguimiento, con
tablero de indicadores y aviso de lluvia.

**Entidades.** `usuarios`, `sectores`, `colonias`, `tipos_dano`, `motivos_rechazo`, `reportes` (baches y encharcamientos),
`confirmaciones`, `historial_estados`, `usuario_colonias`, `notificaciones`.
Relaciones 1:N: sector→colonias, colonia→reportes, usuario→reportes, reporte→historial. Relaciones N:M: usuarios↔reportes
(confirmaciones) y usuarios↔colonias (colonias de interés).

**Servicios externos (desde el backend).** Nominatim/OpenStreetMap (dirección ↔ coordenadas) y Open-Meteo (pronóstico).

**Alcance.** 20 historias indispensables y 8 deseables; el resto queda como trabajo futuro documentado.
