// Clima (sección 13 del contrato): el servidor consulta Open-Meteo; el navegador nunca llama a un servicio externo.
import { api } from './cliente.ts'
import type { AvisoLluvia } from './tipos.ts'

// GET /api/clima/aviso  ->  siempre 200; si el pronóstico falló trae disponible: false
export function pedirAvisoLluvia(): Promise<AvisoLluvia> {
  return api.get<AvisoLluvia>('/api/clima/aviso')
}
