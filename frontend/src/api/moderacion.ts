// Endpoints de moderación (sección 10 del contrato). Solo el rol moderador; el servidor responde 403 a los demás.
import { api, armarConsulta } from './cliente.ts'
import type { FiltroModeracion, Paginacion, RechazarEntrada, ReportePublico, ValidarEntrada } from './tipos.ts'

// GET /api/moderacion/bandeja?colonia_id=&tipo_dano_codigo=&pagina=  ->  baches en Recibido, del más antiguo al más reciente
export function pedirBandeja(filtro: FiltroModeracion): Promise<Paginacion<ReportePublico>> {
  return api.get<Paginacion<ReportePublico>>(`/api/moderacion/bandeja${armarConsulta({ ...filtro })}`)
}

// POST /api/reportes/{id}/validar: 409 TRANSICION_INVALIDA si ya no está en Recibido
export function validarReporte(id: number, datos: ValidarEntrada): Promise<ReportePublico> {
  return api.post<ReportePublico>(`/api/reportes/${id}/validar`, datos)
}

// POST /api/reportes/{id}/rechazar: 422 con `campos` si falta el motivo o su explicación
export function rechazarReporte(id: number, datos: RechazarEntrada): Promise<ReportePublico> {
  return api.post<ReportePublico>(`/api/reportes/${id}/rechazar`, datos)
}
