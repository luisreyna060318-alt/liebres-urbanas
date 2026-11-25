// Administración de usuarios y roles (solo coordinador, sección 12 del contrato).
import { api, armarConsulta } from './cliente.ts'
import type { Paginacion, Rol, UsuarioAdmin } from './tipos.ts'

interface FiltroUsuarios {
  q?: string // parte del nombre o del correo
  rol?: Rol | ''
  pagina?: number
  tam?: number
}

// GET /api/usuarios?q=&rol=&pagina=1&tam=10
export function pedirUsuarios(filtro: FiltroUsuarios = {}): Promise<Paginacion<UsuarioAdmin>> {
  return api.get<Paginacion<UsuarioAdmin>>(`/api/usuarios${armarConsulta({ ...filtro })}`)
}

// PUT /api/usuarios/{id}/rol
export function cambiarRol(id: number, rol: Rol): Promise<UsuarioAdmin> {
  return api.put<UsuarioAdmin>(`/api/usuarios/${id}/rol`, { rol })
}

// PUT /api/usuarios/{id}/suspension: true suspende la cuenta, false la reactiva
export function cambiarSuspension(id: number, suspendido: boolean): Promise<UsuarioAdmin> {
  return api.put<UsuarioAdmin>(`/api/usuarios/${id}/suspension`, { suspendido })
}
