// Qué rutas puede usar cada rol. Una sola tabla alimenta el menú y las rutas protegidas de App.tsx,
// así lo que se ve y lo que se permite no se desfasan.
// Ocultar una opción NO es seguridad: la defensa real es el servidor (403). Esto solo evita mostrar lo que no sirve (HU-01.3 CA1).
import type { Rol } from '../api/tipos.ts'

export interface OpcionMenu {
  ruta: string
  texto: string
  roles: readonly Rol[] | null // null = cualquier persona, con o sin sesión
  soloSinSesion?: boolean // Iniciar sesión y Crear cuenta: se esconden cuando ya hay sesión
}

export const ROLES_CIUDADANO: readonly Rol[] = ['ciudadano']
export const ROLES_MODERADOR: readonly Rol[] = ['moderador']
export const ROLES_COORDINADOR: readonly Rol[] = ['coordinador']
// /moderacion: el coordinador solo entra a registrar el avance de las reparaciones (RN-05)
export const ROLES_SEGUIMIENTO: readonly Rol[] = ['moderador', 'coordinador']

export const OPCIONES_MENU: readonly OpcionMenu[] = [
  { ruta: '/', texto: 'Reportes', roles: null },
  { ruta: '/zona', texto: '¿Cómo está mi zona?', roles: null },
  { ruta: '/mapa', texto: 'Mapa', roles: null },
  { ruta: '/reportar', texto: 'Reportar', roles: ROLES_CIUDADANO },
  { ruta: '/mis-reportes', texto: 'Mis reportes', roles: ROLES_CIUDADANO },
  { ruta: '/perfil', texto: 'Mi perfil', roles: ROLES_CIUDADANO },
  { ruta: '/moderacion', texto: 'Moderación', roles: ROLES_SEGUIMIENTO },
  { ruta: '/admin/colonias', texto: 'Colonias', roles: ROLES_COORDINADOR },
  { ruta: '/admin/usuarios', texto: 'Usuarios', roles: ROLES_COORDINADOR },
  { ruta: '/tablero', texto: 'Tablero', roles: ROLES_COORDINADOR },
  { ruta: '/login', texto: 'Iniciar sesión', roles: null, soloSinSesion: true },
  { ruta: '/registro', texto: 'Crear cuenta', roles: null, soloSinSesion: true },
]

// Opciones que se muestran a quien tiene `rol` (null = no ha iniciado sesión)
export function opcionesParaRol(rol: Rol | null): OpcionMenu[] {
  return OPCIONES_MENU.filter((opcion) => {
    if (opcion.soloSinSesion) return rol === null
    if (opcion.roles === null) return true
    return rol !== null && opcion.roles.includes(rol)
  })
}

// Nombre del rol para mostrarlo en pantalla
export const ETIQUETA_ROL: Record<Rol, string> = {
  ciudadano: 'Ciudadano',
  moderador: 'Moderador',
  coordinador: 'Coordinador',
}
