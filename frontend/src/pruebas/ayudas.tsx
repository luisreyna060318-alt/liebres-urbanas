// Piezas que comparten varias pruebas: usuarios de ejemplo, un contexto de sesión falso y respuestas simuladas de la API.
import { vi } from 'vitest'
import { REGLAS_RESPALDO } from '../api/reglas.ts'
import type { UsuarioPublico } from '../api/tipos.ts'
import { AuthContext } from '../context/AuthContexto.ts'
import type { AuthValor } from '../context/AuthContexto.ts'
import type { ReactNode } from 'react'

export const CIUDADANO: UsuarioPublico = { id: 1, nombre: 'Ana Pérez', correo: 'ana@ejemplo.test', rol: 'ciudadano' }
export const MODERADOR: UsuarioPublico = { id: 2, nombre: 'Mario Ríos', correo: 'mario@ejemplo.test', rol: 'moderador' }
export const COORDINADOR: UsuarioPublico = { id: 3, nombre: 'Clara Soto', correo: 'clara@ejemplo.test', rol: 'coordinador' }

// Valor de sesión para probar componentes sin llamar a la API
export function authFalso(parcial: Partial<AuthValor> = {}): AuthValor {
  const usuario = parcial.usuario ?? null
  return {
    usuario,
    cargando: false,
    aviso: null,
    descartarAviso: vi.fn(),
    login: vi.fn().mockResolvedValue(undefined),
    registro: vi.fn().mockResolvedValue(undefined),
    logout: vi.fn(),
    tienePermiso: (roles) => usuario !== null && roles.includes(usuario.rol),
    ...parcial,
  }
}

export function ConAuth({ valor, children }: { valor: AuthValor; children: ReactNode }) {
  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>
}

// Respuesta JSON como la que devolvería fetch
export function respuestaJson(cuerpo: unknown, status = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status, headers: { 'Content-Type': 'application/json' } })
}

// Reemplaza fetch por una función simulada. `respuestas` se consume una por llamada; GET /api/reglas siempre responde bien.
export function simularFetch(respuestas: Response[] = [], reglas: Partial<typeof REGLAS_RESPALDO> = {}) {
  const pendientes = [...respuestas]
  const simulado = vi.fn((entrada: RequestInfo | URL) => {
    if (String(entrada).endsWith('/api/reglas')) return Promise.resolve(respuestaJson({ ...REGLAS_RESPALDO, ...reglas }))
    const siguiente = pendientes.shift()
    return siguiente ? Promise.resolve(siguiente) : Promise.reject(new TypeError('Failed to fetch'))
  })
  vi.stubGlobal('fetch', simulado)
  return simulado
}

// --- Simulación de la API por ruta (para pantallas que piden varios endpoints) ---
// Cada clave es "MÉTODO /ruta" (sin la parte "?consulta"). El valor es la respuesta, una lista de respuestas
// (se usan en orden y la última se repite) o una función que decide según la petición.
// 'sin_red' simula que no hay conexión. GET /api/reglas siempre responde bien.
export type RespuestaSimulada = { status?: number; cuerpo?: unknown } | 'sin_red'
type Manejador = RespuestaSimulada | RespuestaSimulada[] | ((peticion: { url: URL; cuerpo: unknown }) => RespuestaSimulada)

export interface LlamadaSimulada {
  clave: string
  url: URL
  cuerpo: unknown
}

export function simularApi(rutas: Record<string, Manejador>, reglas: Partial<typeof REGLAS_RESPALDO> = {}) {
  const llamadas: LlamadaSimulada[] = []
  const usadas = new Map<string, number>()

  const simulado = vi.fn((entrada: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(entrada))
    const clave = `${init?.method ?? 'GET'} ${url.pathname}`
    const cuerpo: unknown = typeof init?.body === 'string' ? JSON.parse(init.body) : undefined
    llamadas.push({ clave, url, cuerpo })

    if (clave === 'GET /api/reglas') return Promise.resolve(respuestaJson({ ...REGLAS_RESPALDO, ...reglas }))

    const manejador = rutas[clave]
    if (manejador === undefined) return Promise.reject(new TypeError('Failed to fetch'))

    let respuesta: RespuestaSimulada
    if (typeof manejador === 'function') {
      respuesta = manejador({ url, cuerpo })
    } else if (Array.isArray(manejador)) {
      const vez = usadas.get(clave) ?? 0
      usadas.set(clave, vez + 1)
      respuesta = manejador[Math.min(vez, manejador.length - 1)]
    } else {
      respuesta = manejador
    }

    if (respuesta === 'sin_red') return Promise.reject(new TypeError('Failed to fetch'))
    const status = respuesta.status ?? 200
    if (status === 204) return Promise.resolve(new Response(null, { status }))
    return Promise.resolve(respuestaJson(respuesta.cuerpo, status))
  })

  vi.stubGlobal('fetch', simulado)
  return {
    simulado,
    llamadas,
    // Las llamadas que se hicieron a una ruta, por ejemplo de('POST /api/reportes/baches')
    de: (clave: string) => llamadas.filter((l) => l.clave === clave),
  }
}

// Simula navigator.geolocation (jsdom no lo trae). preparar.ts lo quita al terminar cada prueba.
export function simularGeolocalizacion(resultado: { lat: number; lon: number } | { codigo: number }) {
  const getCurrentPosition = vi.fn((alExito: (p: unknown) => void, alError: (e: unknown) => void) => {
    if ('codigo' in resultado) alError({ code: resultado.codigo, message: 'simulado' })
    else alExito({ coords: { latitude: resultado.lat, longitude: resultado.lon } })
  })
  Object.defineProperty(navigator, 'geolocation', { value: { getCurrentPosition }, configurable: true })
  return getCurrentPosition
}
