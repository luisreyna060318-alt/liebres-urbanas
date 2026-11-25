// Guarda la sesión (token y usuario) en sessionStorage: se borra al cerrar la pestaña.
// Todo va dentro de try/catch porque el navegador puede bloquear el almacenamiento (modo privado, etc.);
// en ese caso la sesión vive solo en memoria y se pierde al recargar. Nunca se imprime el token en consola.
import type { UsuarioPublico } from './tipos.ts'

const CLAVE_TOKEN = 'liebre-urbana-token'
const CLAVE_USUARIO = 'liebre-urbana-usuario'

let tokenEnMemoria: string | null = null

function leerAlmacen(clave: string): string | null {
  try {
    return sessionStorage.getItem(clave)
  } catch {
    return null
  }
}

function escribirAlmacen(clave: string, valor: string): void {
  try {
    sessionStorage.setItem(clave, valor)
  } catch {
    // Si no se puede guardar, la memoria basta mientras la pestaña siga abierta
  }
}

function borrarAlmacen(clave: string): void {
  try {
    sessionStorage.removeItem(clave)
  } catch {
    // Nada que hacer
  }
}

export function leerToken(): string | null {
  return tokenEnMemoria ?? leerAlmacen(CLAVE_TOKEN)
}

export function leerUsuarioGuardado(): UsuarioPublico | null {
  const texto = leerAlmacen(CLAVE_USUARIO)
  if (!texto) return null
  try {
    return JSON.parse(texto) as UsuarioPublico
  } catch {
    return null
  }
}

export function guardarSesion(token: string, usuario: UsuarioPublico): void {
  tokenEnMemoria = token
  escribirAlmacen(CLAVE_TOKEN, token)
  escribirAlmacen(CLAVE_USUARIO, JSON.stringify(usuario))
}

export function borrarSesion(): void {
  tokenEnMemoria = null
  borrarAlmacen(CLAVE_TOKEN)
  borrarAlmacen(CLAVE_USUARIO)
}
