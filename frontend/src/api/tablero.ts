// Tablero de indicadores (sección 14 del contrato). Solo coordinador: el servidor responde 401/403 a los demás.
import { api, armarConsulta } from './cliente.ts'
import type { FiltroTablero, Tablero } from './tipos.ts'

// GET /api/tablero?desde=&hasta=&sector_id=
export function pedirTablero(filtro: FiltroTablero = {}): Promise<Tablero> {
  return api.get<Tablero>(`/api/tablero${armarConsulta({ ...filtro })}`)
}
