# Auditoría de accesibilidad y responsividad (RNF-01 y RNF-02)

Evidencia del criterio 2 de la rúbrica (HTML semántico, CSS y responsividad). Se midió con **axe-core** (reglas WCAG 2.0, 2.1 y 2.2 de
nivel A y AA) y con **Lighthouse** (categoría Accesibilidad), en las 12 vistas principales, en **móvil (360 px)** y en **escritorio
(1280 px)**. También se comprobó que ninguna vista tenga desborde horizontal a 360 px.

- Datos: `resultados.json` (una fila por vista y dispositivo). Capturas de pantalla completa en [`../capturas/`](../capturas/).
- Se repite con `docs/herramientas/auditar_accesibilidad.mjs` (las herramientas se instalan aparte; las instrucciones van en su cabecera).

## Resultado

| Vista | Ruta | Rol | Lighthouse móvil | Lighthouse escritorio | axe (violaciones) | Desborde a 360 px |
|---|---|---|---|---|---|---|
| Reportes (consulta) | `/` | público | 100 | 100 | 0 | no |
| Detalle de un reporte | `/reportes/:id` | público | 100 | 100 | 0 | no |
| ¿Cómo está mi zona? | `/zona` | público | 100 | 100 | 0 | no |
| Iniciar sesión | `/login` | público | 100 | 100 | 0 | no |
| Crear cuenta | `/registro` | público | 100 | 100 | 0 | no |
| Aviso de privacidad | `/privacidad` | público | 100 | 100 | 0 | no |
| Reportar | `/reportar` | ciudadano | 100 | 100 | 0 | no |
| Mis reportes | `/mis-reportes` | ciudadano | 100 | 100 | 0 | no |
| Moderación | `/moderacion` | moderador | 100 | 100 | 0 | no |
| Tablero | `/tablero` | coordinador | 100 | 100 | 0 | no |
| Administrar colonias | `/admin/colonias` | coordinador | 100 | 100 | 0 | no |
| Administrar usuarios | `/admin/usuarios` | coordinador | 100 | 100 | 0 | no |

Meta del proyecto: Lighthouse de accesibilidad ≥ 90 en las vistas principales. Se cumple en todas (mínimo 100).

## Qué se encontró y se corrigió durante la auditoría

La primera pasada no salió limpia; estos fueron los hallazgos reales y cómo se resolvieron:

1. **Desborde horizontal a 360 px en `/admin/colonias` y `/admin/usuarios`.** La tabla vivía dentro de un contenedor con scroll
   propio, pero Chrome móvil ensanchaba toda la página con el ancho de la tabla (la página medía 643 px en una pantalla de 375).
   Se resolvió con `contain: layout` en el contenedor; la tabla sigue desplazándose dentro de su caja. Corregido en las ramas de
   esas historias (C8 y C9).
2. **Lighthouse 98 en `/mis-reportes`** por orden de encabezados (`heading-order`): pasaba de `h1` a `h3` sin un `h2`. Se agregó un
   `h2` solo para lectores de pantalla ("Lista de tus reportes"). Corregido en este PR.

## Cómo se hizo y qué NO cubre

- Navegador: Microsoft Edge (Chromium) sin interfaz, controlado con `puppeteer-core`; Lighthouse en modo de navegación con el mismo
  navegador para conservar la sesión de cada rol. Las vistas privadas se auditaron con las cuentas de demostración (ficticias).
- Se midió sobre la aplicación **compilada** (`vite preview`) con la base de datos sembrada (500 reportes), en una computadora local, no
  en la URL pública. Solo se midió la categoría Accesibilidad (no rendimiento ni SEO).
- Las herramientas automáticas encuentran una parte de los problemas (suelen cubrir una fracción de los criterios WCAG). **No
  sustituyen** la revisión manual con teclado y lector de pantalla ni las pruebas en dispositivos reales, que no se hicieron
  aquí. El estado "Pronóstico no disponible", los mensajes de error del servidor y los formularios abiertos (por ejemplo el de
  rechazo) solo se revisaron en el estado inicial de cada vista.
- Las capturas son del build integrado de `main` más los PRs de consulta, detalle, zona, moderación, administración, tablero y aviso de
  lluvia, que al momento de la medición estaban abiertos. Conviene repetir la auditoría sobre `main` cuando todo esté fusionado y sobre
  la URL desplegada.
