// Endpoints de cuenta y sesión (sección 3 del contrato).
import { api } from './cliente.ts'
import type { DatosLogin, DatosRegistro, SesionRespuesta, UsuarioPublico } from './tipos.ts'

// POST /api/auth/registro (201): crea la cuenta con rol ciudadano y deja a la persona dentro
export function registrar(datos: DatosRegistro): Promise<SesionRespuesta> {
  return api.post<SesionRespuesta>('/api/auth/registro', datos)
}

// POST /api/auth/login
export function iniciarSesion(datos: DatosLogin): Promise<SesionRespuesta> {
  return api.post<SesionRespuesta>('/api/auth/login', datos)
}

// POST /api/auth/refresh: cambia el token vigente por uno nuevo de 30 minutos
export function renovarSesion(): Promise<SesionRespuesta> {
  return api.post<SesionRespuesta>('/api/auth/refresh')
}

// GET /api/auth/yo: la persona dueña del token actual (con el rol que tiene hoy en la base)
export function pedirYo(): Promise<UsuarioPublico> {
  return api.get<UsuarioPublico>('/api/auth/yo')
}
