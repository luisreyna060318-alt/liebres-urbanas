import { createContext, useContext } from 'react'
import type { DatosRegistro, Rol, UsuarioPublico } from '../api/tipos.ts'

// Lo que cualquier componente puede leer de la sesión
export interface AuthValor {
  usuario: UsuarioPublico | null
  cargando: boolean // true mientras se comprueba si el token guardado sigue siendo válido
  aviso: string | null // mensaje breve cuando la sesión caducó o se cerró por inactividad
  descartarAviso: () => void
  login: (correo: string, password: string) => Promise<void>
  registro: (datos: DatosRegistro) => Promise<void>
  logout: () => void
  salioPorSuCuenta: boolean // true tras cerrar sesión a mano: la pantalla donde estaba no se recuerda
  // true si hay sesión y el rol de la persona está en la lista. Solo decide qué mostrar: el servidor vuelve a validar.
  tienePermiso: (roles: readonly Rol[]) => boolean
}

// El proveedor está en AuthProvider.tsx. El contexto se exporta aparte para que las pruebas
// puedan darle un valor falso a los componentes sin llamar a la API.
export const AuthContext = createContext<AuthValor | null>(null)

// Hook para leer la sesión desde cualquier componente
export function useAuth(): AuthValor {
  const valor = useContext(AuthContext)
  if (!valor) throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  return valor
}
