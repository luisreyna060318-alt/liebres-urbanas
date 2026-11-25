// Endpoints de moderación (sección 10 del contrato). Bandeja, validar y rechazar: solo el rol moderador.
// Seguimiento y avance de la reparación: moderador o coordinador. El servidor responde 403 a los demás.
import { api, armarConsulta } from './cliente.ts'
import type {
  AvanceEntrada,
  FiltroModeracion,
  FiltroSeguimiento,
  Paginacion,
  RechazarEntrada,
  ReportePublico,
  ValidarEntrada,
} from './tipos.ts'

// GET /api/moderacion/seguimiento?estado=&colonia_id=&tipo_dano_codigo=&pagina=  ->  validados y en reparación
export function pedirSeguimiento(filtro: FiltroSeguimiento): Promise<Paginacion<ReportePublico>> {
  return api.get<Paginacion<ReportePublico>>(`/api/moderacion/seguimiento${armarConsulta({ ...filtro })}`)
}

// POST /api/reportes/{id}/estado: 409 TRANSICION_INVALIDA si el salto no sigue RN-05; 422 con campos.fecha_reparacion
export function registrarAvance(id: number, datos: AvanceEntrada): Promise<ReportePublico> {
  return api.post<ReportePublico>(`/api/reportes/${id}/estado`, datos)
}

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
