// Piezas comunes de los formularios de moderación (validar, rechazar y, en seguimiento, cambiar el estado).
import { ErrorApi } from '../../api/cliente.ts'
import type { ReportePublico } from '../../api/tipos.ts'

export interface PropsAccion {
  reporte: ReportePublico
  alTerminar: (mensaje: string) => void // la acción salió bien
  alDesfasarse: (mensaje: string) => void // el reporte ya cambió (409/404): hay que refrescar la lista
  alCancelar: () => void
}

// Errores que significan "la lista que ves ya no es la actual" (otra persona ya cambió el reporte)
export function estaDesfasado(e: unknown): e is ErrorApi {
  return e instanceof ErrorApi && (e.codigo === 'TRANSICION_INVALIDA' || e.codigo === 'NO_ENCONTRADO')
}
