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
