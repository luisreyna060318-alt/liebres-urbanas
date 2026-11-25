// ¿Cómo está mi zona? (sección 9 del contrato). Endpoint público: no necesita sesión.
import { api, armarConsulta } from './cliente.ts'
import type { ZonaRespuesta } from './tipos.ts'

// GET /api/zona?lat=..&lon=..  ->  reportes activos a 1 km. 422 FUERA_DEL_MUNICIPIO si el punto no está en Juárez.
export function pedirZona(lat: number, lon: number): Promise<ZonaRespuesta> {
  return api.get<ZonaRespuesta>(`/api/zona${armarConsulta({ lat, lon })}`)
}
