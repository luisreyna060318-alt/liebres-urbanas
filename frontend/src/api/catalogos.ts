// Catálogos de solo lectura (sección 4 del contrato). Los usan los formularios y los filtros de otras pantallas.
import { api, armarConsulta } from './cliente.ts'
import type {
  Colonia,
  EdicionColonia,
  EntradaSector,
  MotivoRechazo,
  NuevaColonia,
  Paginacion,
  Sector,
  TipoDano,
} from './tipos.ts'

// GET /api/sectores
export function pedirSectores(): Promise<Sector[]> {
  return api.get<Sector[]>('/api/sectores')
}

interface FiltroColonias {
  q?: string
  sector_id?: number
  solo_activas?: boolean // por omisión el servidor solo devuelve las activas
  pagina?: number
  tam?: number // hasta 500 para llenar listas desplegables
}

// GET /api/colonias?q=&sector_id=&solo_activas=true&pagina=1&tam=50
export function pedirColonias(filtro: FiltroColonias = {}): Promise<Paginacion<Colonia>> {
  return api.get<Paginacion<Colonia>>(`/api/colonias${armarConsulta({ ...filtro })}`)
}

// GET /api/tipos-dano (solo los activos)
export function pedirTiposDano(): Promise<TipoDano[]> {
  return api.get<TipoDano[]>('/api/tipos-dano')
}

// GET /api/motivos-rechazo (solo los activos)
export function pedirMotivosRechazo(): Promise<MotivoRechazo[]> {
  return api.get<MotivoRechazo[]>('/api/motivos-rechazo')
}

// --- Administración (solo coordinador, sección 11 del contrato) ---

// POST /api/colonias (201)
export function crearColonia(datos: NuevaColonia): Promise<Colonia> {
  return api.post<Colonia>('/api/colonias', datos)
}

// PUT /api/colonias/{id}: se envía todo; `activa: false` la desactiva
export function actualizarColonia(id: number, datos: EdicionColonia): Promise<Colonia> {
  return api.put<Colonia>(`/api/colonias/${id}`, datos)
}

// DELETE /api/colonias/{id} (204). Con reportes responde 409: solo se puede desactivar
export function borrarColonia(id: number): Promise<void> {
  return api.delete<void>(`/api/colonias/${id}`)
}

// POST /api/sectores (201)
export function crearSector(datos: EntradaSector): Promise<Sector> {
  return api.post<Sector>('/api/sectores', datos)
}

// PUT /api/sectores/{id}
export function renombrarSector(id: number, datos: EntradaSector): Promise<Sector> {
  return api.put<Sector>(`/api/sectores/${id}`, datos)
}
