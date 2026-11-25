// Traduce los errores de la API a mensajes para la persona. Los usan los formularios de reporte y las confirmaciones.
import { ErrorApi } from '../api/cliente.ts'

export interface ErrorDeEnvio {
  mensaje: string // se muestra arriba del botón de enviar
  campos: Record<string, string> // mensajes por campo (solo en los 422 de validación)
}

// Qué decirle a la persona cuando falla el envío de un reporte (HU-02.1 CA2 y CA4, RN-08).
// Los datos capturados nunca se borran: el mensaje lo dice para que nadie los vuelva a escribir.
export function interpretarErrorEnvio(error: unknown, maxReportesPorHora: number): ErrorDeEnvio {
  if (!(error instanceof ErrorApi)) {
    return { mensaje: 'No se pudo enviar el reporte. Tus datos siguen aquí; inténtalo de nuevo.', campos: {} }
  }

  switch (error.codigo) {
    case 'SIN_CONEXION':
      return {
        mensaje: 'No se pudo conectar con el servidor. Tus datos siguen aquí: revisa tu conexión y vuelve a enviar.',
        campos: {},
      }
    case 'FUERA_DEL_MUNICIPIO':
      return {
        mensaje:
          'Esa ubicación está fuera de Ciudad Juárez, así que no se puede registrar. Busca otra dirección o corrige las coordenadas.',
        campos: {},
      }
    case 'LIMITE_HORARIO':
      return {
        mensaje: `Llegaste al límite de ${maxReportesPorHora} reportes por hora. Inténtalo de nuevo más tarde; tus datos siguen aquí.`,
        campos: {},
      }
    default:
      // VALIDACION trae `campos`; cualquier otro código trae solo el mensaje del servidor
      return { mensaje: error.detail, campos: error.campos }
  }
}

// Mensaje cuando falla una confirmación ("Sigue ahí", "Ya no hay agua", "Confirmar este reporte")
export function mensajeErrorConfirmacion(error: unknown): string {
  if (!(error instanceof ErrorApi)) return 'No se pudo registrar tu respuesta. Inténtalo de nuevo.'
  if (error.codigo === 'YA_CONFIRMADO') return 'Ya respondiste sobre este reporte.'
  if (error.codigo === 'ES_TU_REPORTE') return 'No puedes confirmar tu propio reporte.'
  return error.detail
}
