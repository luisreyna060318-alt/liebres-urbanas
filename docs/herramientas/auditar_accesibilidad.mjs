// Audita la accesibilidad de las vistas principales: axe-core (WCAG 2.2 AA) y Lighthouse (categoría accesibilidad),
// en móvil (360 px) y escritorio. También toma capturas y detecta desborde horizontal (RNF-01 y RNF-02).
//
// NO es una dependencia del proyecto: las herramientas se instalan APARTE, fuera del repositorio:
//   mkdir ../herramientas-a11y && cd ../herramientas-a11y && npm init -y && npm install lighthouse axe-core puppeteer-core
//
// Uso (con el backend en :8000, el frontend en :5173 y la semilla cargada; las cuentas de demostración están en el README):
//   HERRAMIENTAS=/ruta/a/herramientas-a11y node docs/herramientas/auditar_accesibilidad.mjs <carpeta_salida> [vistas_separadas_por_comas]
// Variables opcionales: NAVEGADOR (ruta de Edge o Chrome) y BASE (por omisión http://localhost:5173).
// Obligatoria: PASSWORD_DEMO (contraseña de las cuentas de demostración del entorno local).
// En Git Bash de Windows pasa la carpeta de salida como ruta de Windows (C:/...) o con MSYS_NO_PATHCONV sin definir.
import { createRequire } from 'node:module'
import { pathToFileURL } from 'node:url'
import fs from 'node:fs'
import path from 'node:path'

// Carpeta (fuera del repo) donde se instalaron lighthouse, axe-core y puppeteer-core; createRequire pide la barra final
const HERR = path.resolve(process.env.HERRAMIENTAS ?? '../herramientas-a11y').split(path.sep).join('/') + '/'
const require = createRequire(HERR)
const puppeteer = require('puppeteer-core')
const axeSource = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8')
const { default: lighthouse } = await import(pathToFileURL(path.resolve(HERR, 'node_modules/lighthouse/core/index.js')).href)

const BASE = process.env.BASE ?? 'http://localhost:5173'
// La contraseña de las cuentas de demostración se pasa por variable de entorno (sin valor por omisión en el código)
const PASSWORD = process.env.PASSWORD_DEMO
if (!PASSWORD) {
  console.error('Define PASSWORD_DEMO con la contraseña de las cuentas de demostración del entorno local (ver el README).')
  process.exit(1)
}
const EDGE = process.env.NAVEGADOR ?? 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const salida = path.resolve(process.argv[2] ?? './a11y-out')
const filtro = process.argv[3] ?? ''
fs.mkdirSync(salida, { recursive: true })

// rol -> rutas. Se muestra la ruta con un id real de reporte.
const RUTAS = [
  { rol: null, ruta: '/', nombre: 'consulta' },
  { rol: null, ruta: '/reportes/1', nombre: 'detalle' },
  { rol: null, ruta: '/zona', nombre: 'zona' },
  { rol: null, ruta: '/login', nombre: 'login' },
  { rol: null, ruta: '/registro', nombre: 'registro' },
  { rol: null, ruta: '/privacidad', nombre: 'privacidad' },
  { rol: 'ciudadano', ruta: '/reportar', nombre: 'reportar' },
  { rol: 'ciudadano', ruta: '/mis-reportes', nombre: 'mis-reportes' },
  { rol: 'moderador', ruta: '/moderacion', nombre: 'moderacion' },
  { rol: 'coordinador', ruta: '/tablero', nombre: 'tablero' },
  { rol: 'coordinador', ruta: '/admin/colonias', nombre: 'admin-colonias' },
  { rol: 'coordinador', ruta: '/admin/usuarios', nombre: 'admin-usuarios' },
  // Vistas de la pasada final (26-nov). Los ids salen de la semilla, que es determinista: el reporte 500 es un
  // encharcamiento activo y el 1 es un bache validado (compruébalo con GET /api/reportes si cambia la semilla).
  { rol: 'coordinador', ruta: '/moderacion', nombre: 'moderacion-coordinador' },
  { rol: 'ciudadano', ruta: '/reportes/500', nombre: 'detalle-encharcamiento-ciudadano' },
  { rol: 'ciudadano', ruta: '/reportes/1', nombre: 'detalle-bache-ciudadano' },
  { rol: 'moderador', ruta: '/reportes/500', nombre: 'detalle-encharcamiento-moderador' },
  { rol: 'moderador', ruta: '/reportes/1', nombre: 'detalle-bache-moderador' },
].filter((r) => !filtro || filtro.split(',').includes(r.nombre))

const VISTAS = {
  movil: { width: 360, height: 800, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
  escritorio: { width: 1280, height: 800, deviceScaleFactor: 1 },
}
const PANTALLA_LH = {
  movil: { mobile: true, width: 360, height: 800, deviceScaleFactor: 2, disabled: false },
  escritorio: { mobile: false, width: 1280, height: 800, deviceScaleFactor: 1, disabled: false },
}

const navegador = await puppeteer.launch({
  executablePath: EDGE,
  headless: true,
  args: ['--remote-debugging-port=9333', '--no-first-run', '--disable-extensions'],
})

async function esperarContenido(page) {
  await page.waitForNetworkIdle({ idleTime: 600, timeout: 15000 }).catch(() => {})
  await page.waitForFunction(() => !/Cargando/.test(document.querySelector('main')?.innerText ?? ''), { timeout: 8000 }).catch(() => {})
}

async function entrar(page, rol) {
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle0' })
  await page.evaluate(() => sessionStorage.clear())
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle0' })
  await page.type('input[type="email"]', `${rol}@liebreurbana.test`)
  await page.type('input[type="password"]', PASSWORD)
  await Promise.all([page.keyboard.press('Enter'), page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }).catch(() => {})])
}

const resultados = []
const rolActual = { v: undefined }
const page = await navegador.newPage()

for (const r of RUTAS) {
  if (r.rol !== rolActual.v) {
    await page.setViewport(VISTAS.escritorio)
    if (r.rol) await entrar(page, r.rol)
    else {
      await page.goto(`${BASE}/login`, { waitUntil: 'networkidle0' })
      await page.evaluate(() => sessionStorage.clear())
    }
    rolActual.v = r.rol
  }
  for (const vista of ['movil', 'escritorio']) {
    const fila = { nombre: r.nombre, ruta: r.ruta, rol: r.rol ?? 'publico', vista }
    try {
      await page.setViewport(VISTAS[vista])
      await page.goto(BASE + r.ruta, { waitUntil: 'networkidle0' })
      await esperarContenido(page)
      fila.url_final = new URL(page.url()).pathname

      // Capturas (evidencia RNF-01)
      await page.screenshot({ path: path.join(salida, `${r.nombre}-${vista}.png`), fullPage: true })

      // Desborde horizontal (RNF-01)
      fila.desborde_horizontal = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)

      // axe-core, WCAG 2.2 AA
      await page.evaluate(axeSource)
      const axe = await page.evaluate(() =>
        axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'] } }),
      )
      fila.axe = axe.violations.map((v) => ({
        id: v.id,
        impacto: v.impact,
        ayuda: v.help,
        nodos: v.nodes.length,
        ejemplo: v.nodes[0]?.target?.join(' '),
      }))

      // Lighthouse (solo accesibilidad), con el mismo navegador para conservar la sesión
      const lh = await lighthouse(
        BASE + r.ruta,
        {
          output: 'json',
          logLevel: 'error',
          onlyCategories: ['accessibility'],
          formFactor: vista === 'movil' ? 'mobile' : 'desktop',
          screenEmulation: PANTALLA_LH[vista],
          throttlingMethod: 'provided',
          disableStorageReset: true,
        },
        undefined,
        page,
      )
      fila.lighthouse = Math.round((lh.lhr.categories.accessibility.score ?? 0) * 100)
      fila.lh_fallos = Object.values(lh.lhr.audits)
        .filter((a) => a.score !== null && a.score < 1 && a.scoreDisplayMode === 'binary')
        .map((a) => a.id)
    } catch (e) {
      fila.error = String(e).slice(0, 300)
    }
    resultados.push(fila)
    console.log(
      `${fila.nombre.padEnd(15)} ${vista.padEnd(10)} LH=${fila.lighthouse ?? '?'} axe=${fila.axe?.length ?? '?'} desborde=${fila.desborde_horizontal} fin=${fila.url_final} lh_fallos=${(fila.lh_fallos ?? []).join(',')} ${fila.error ?? ''}`,
    )
  }
}

fs.writeFileSync(path.join(salida, 'resultados.json'), JSON.stringify(resultados, null, 2))
await navegador.close()
