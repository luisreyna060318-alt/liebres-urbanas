// Piezas comunes de los formularios de moderación (validar, rechazar y, en seguimiento, cambiar el estado).
import { ErrorApi } from '../../api/cliente.ts'
import type { ReportePublico } from '../../api/tipos.ts'
import { ZONA_HORARIA } from '../../utils/fechas.ts'

// Día del calendario en Ciudad Juárez como "AAAA-MM-DD" (el formato de <input type="date">).
// Se usa para el máximo (hoy) y el mínimo (día del reporte) de la fecha de reparación.
export function diaEnJuarez(fecha: Date): string {
  const formato = new Intl.DateTimeFormat('en-CA', { timeZone: ZONA_HORARIA, year: 'numeric', month: '2-digit', day: '2-digit' })
  return formato.format(fecha)
}

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
