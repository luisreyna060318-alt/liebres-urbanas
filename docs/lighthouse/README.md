# Auditoría de accesibilidad y responsividad (RNF-01 y RNF-02)

Evidencia del criterio 2 de la rúbrica (HTML semántico, CSS y responsividad). Se midió con **axe-core** (reglas WCAG 2.0, 2.1 y 2.2 de
nivel A y AA) y con **Lighthouse** (categoría Accesibilidad), en **móvil (360 px)** y en **escritorio (1280 px)**. También se comprobó
que ninguna vista tenga desborde horizontal a 360 px.

Hay dos pasadas: la **primera** (antes de fusionar las historias de moderación, severidad y filtro por sector) y la **final**
(26 de noviembre de 2026), que repite todo sobre `main` ya integrado y agrega las vistas nuevas. Los números de abajo son los de la
pasada final.

- Datos: `resultados.json` es un **resumen** (una fila por vista, dispositivo y entorno: `local` o `desplegado`) que armé a partir de
  la salida del script; la salida cruda (con cada violación de axe y cada auditoría de Lighthouse) no se guarda en el repositorio y se
  regenera con el script.
- Capturas: [`../capturas/`](../capturas/) son **de la primera pasada**; en la pasada final no se subieron capturas nuevas
  (pesan unos 5 MB).
- Se repite con `docs/herramientas/auditar_accesibilidad.mjs` (las herramientas se instalan aparte; las instrucciones van en su cabecera).

## Qué se midió exactamente (pasada final)

- **Código medido:** `main` en el commit `06d977c` (fusión del PR #85), que ya incluye #33, #35 y #81 a #84. Mientras corría la
  medición `origin/main` avanzó a `77ab1f4` (PR #87 y #88), pero esos cambios son solo de documentación (`README.md`,
  `AI_USAGE.md`, `docs/`): `frontend/`, `backend/` y `db/` son idénticos.
- **Entorno local:** base PostgreSQL nueva (migrada con Alembic y sembrada con `db/seed.py`: 500 reportes ficticios), API con uvicorn
  en el puerto 8000 y frontend **compilado** servido con `vite preview` en el 5173. Cuentas de demostración (ficticias) para cada rol.
- **Entorno desplegado:** `https://liebre-urbana.vercel.app` (API en `https://liebre-urbana-api.onrender.com`). `GET /api/health` devolvió
  `version` = `9847f5f`, que es la fusión del PR #87; su única diferencia con el commit medido en local es `README.md`, así que
  **la aplicación desplegada es la misma** que la local en código. Ya no es la punta de `origin/main` (`77ab1f4`), pero lo que falta por
  desplegar es solo documentación.
- **Herramientas:** Lighthouse 13.6.0, axe-core 4.14.1, puppeteer-core 25.19.0, Microsoft Edge 158 sin interfaz, Node 26.

## Resultado en local (17 vistas)

Todas las filas: Lighthouse de accesibilidad **100** en móvil y en escritorio, **0** violaciones de axe y **sin** desborde horizontal a 360 px.

| Vista | Ruta | Rol | Lighthouse móvil | Lighthouse escritorio | axe (violaciones) | Desborde a 360 px |
|---|---|---|---|---|---|---|
| Reportes (consulta) | `/` | público | 100 | 100 | 0 | no |
| Detalle de un reporte (bache) | `/reportes/:id` | público | 100 | 100 | 0 | no |
| ¿Cómo está mi zona? | `/zona` | público | 100 | 100 | 0 | no |
| Iniciar sesión | `/login` | público | 100 | 100 | 0 | no |
| Crear cuenta | `/registro` | público | 100 | 100 | 0 | no |
| Aviso de privacidad | `/privacidad` | público | 100 | 100 | 0 | no |
| Reportar | `/reportar` | ciudadano | 100 | 100 | 0 | no |
| Mis reportes | `/mis-reportes` | ciudadano | 100 | 100 | 0 | no |
| Moderación (con "Por revisar" y "En seguimiento") | `/moderacion` | moderador | 100 | 100 | 0 | no |
| Tablero | `/tablero` | coordinador | 100 | 100 | 0 | no |
| Administrar colonias | `/admin/colonias` | coordinador | 100 | 100 | 0 | no |
| Administrar usuarios | `/admin/usuarios` | coordinador | 100 | 100 | 0 | no |
| **Nueva:** Moderación, solo "En seguimiento" | `/moderacion` | coordinador | 100 | 100 | 0 | no |
| **Nueva:** Detalle de un encharcamiento ("Sigue ahí" y "Ya no hay agua") | `/reportes/:id` | ciudadano | 100 | 100 | 0 | no |
| **Nueva:** Detalle de un encharcamiento ("Rechazar este reporte") | `/reportes/:id` | moderador | 100 | 100 | 0 | no |
| **Nueva:** Detalle de un bache (confirmar o desmentir) | `/reportes/:id` | ciudadano | 100 | 100 | 0 | no |
| **Nueva:** Detalle de un bache validado (no mostró botón "Rechazar") | `/reportes/:id` | moderador | 100 | 100 | 0 | no |

En `resultados.json` los detalles se identifican como `detalle-encharcamiento-ciudadano`, `detalle-encharcamiento-moderador`,
`detalle-bache-ciudadano` y `detalle-bache-moderador`; la moderación del coordinador, como `moderacion-coordinador`. El encharcamiento
medido fue el `/reportes/500` de la semilla (los encharcamientos activos vencen a las 6 horas, así que ese id solo existe al
sembrar de nuevo). La vista del coordinador mostró únicamente la pestaña "En seguimiento", como pide la regla de roles.

## Resultado en la URL desplegada (solo vistas públicas)

Misma herramienta y mismas métricas, contra `https://liebre-urbana.vercel.app` con la API de Render. Sin iniciar sesión.

| Vista | Ruta | Lighthouse móvil | Lighthouse escritorio | axe (violaciones) | Desborde a 360 px |
|---|---|---|---|---|---|
| Reportes (consulta) | `/` | 100 | 100 | 0 | no |
| Detalle de un reporte | `/reportes/1` | 100 | 100 | 0 | no |
| ¿Cómo está mi zona? | `/zona` | 100 | 100 | 0 | no |
| Iniciar sesión | `/login` | 100 | 100 | 0 | no |
| Crear cuenta | `/registro` | 100 | 100 | 0 | no |
| Aviso de privacidad | `/privacidad` | 100 | 100 | 0 | no |

Coincide con lo medido en local en las seis vistas públicas. Meta del proyecto: Lighthouse de accesibilidad ≥ 90 en las vistas
principales; se cumple en todas las vistas medidas (mínimo 100).

## Qué cambió desde la primera pasada

- **Vistas nuevas medidas:** moderación del coordinador (pestaña "En seguimiento"), detalle de encharcamiento con los botones
  "Sigue ahí", "Ya no hay agua" y "Rechazar este reporte", y detalle de bache como ciudadano y como moderador (confirmar y desmentir desde el detalle). La severidad en las tarjetas (consulta y moderación) y el filtro por sector (consulta) quedan cubiertos al medir esas
  vistas de nuevo.
- **Resultado:** ninguna regresión; las 12 vistas de la primera pasada siguen en 100 / 0 / sin desborde, y las 5 nuevas salen igual.
- **Correcciones de la primera pasada que siguen vigentes:** `contain: layout` en las tablas de administración (sin desborde a 360 px)
  y el `h2` de `/mis-reportes` (orden de encabezados).
- **Nuevo en esta pasada:** la medición ya se hace también sobre la URL desplegada (solo vistas públicas).

## Observación fuera de las métricas automáticas

Al abrir el formulario de rechazo en el detalle (moderador), el botón "Rechazar este reporte" desaparece y el foco del teclado se va
al `body` (no hay `.focus()` en `FormularioRechazo.tsx`). axe no lo marca como violación (da 0, con el formulario abierto, a 360 px)
y no afecta a Lighthouse, pero conviene revisarlo con teclado y lector de pantalla (WCAG 2.4.3, orden del foco): mover el foco al
primer campo del formulario al abrirlo y devolverlo al botón al cancelar.

## Cómo se hizo y qué NO cubre

- Navegador: Microsoft Edge (Chromium) sin interfaz, controlado con `puppeteer-core`; Lighthouse en modo de navegación con el mismo
  navegador para conservar la sesión de cada rol. Las vistas privadas se auditaron con las cuentas de demostración (ficticias), solo en
  local.
- Solo se midió la categoría Accesibilidad (no rendimiento ni SEO).
- **No hubo revisión manual con lector de pantalla** (NVDA, VoiceOver, TalkBack) ni pruebas en dispositivos reales. Las herramientas
  automáticas encuentran una parte de los problemas (suelen cubrir una fracción de los criterios WCAG) y **no las sustituyen**. La
  navegación completa solo con teclado tampoco se recorrió a mano.
- **Las vistas con rol (ciudadano, moderador, coordinador) no se midieron en producción**: ahí no se inició sesión a propósito. Se
  midieron en local, que ejecuta el mismo código.
- Solo se revisó el estado inicial de cada vista, salvo el formulario de rechazo del detalle de encharcamiento, que se midió abierto
  con axe a 360 px. Siguen sin medirse: "Pronóstico no disponible", los mensajes de error del servidor, los resultados de las acciones
  ("Sigue ahí", confirmar, desmentir) y el formulario de rechazo de la bandeja "Por revisar".
