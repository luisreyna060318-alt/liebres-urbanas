import { describe, expect, it } from 'vitest'
import { diasDesde, formatoFecha, formatoFechaHora } from './fechas.ts'

describe('formatoFecha y formatoFechaHora (hora de Ciudad Juárez)', () => {
  it('cerca de la medianoche UTC todavía es el día anterior en Juárez', () => {
    // 02:30 UTC del 24 de noviembre = 19:30 del 23 de noviembre en Juárez (UTC-7 en invierno)
    expect(formatoFecha('2026-11-24T02:30:00Z')).toBe('23 nov 2026')
    expect(formatoFechaHora('2026-11-24T02:30:00Z')).toBe('23 nov 2026, 19:30')
  })

  it('en verano usa UTC-6 (horario de verano)', () => {
    // 05:30 UTC del 1 de julio = 23:30 del 30 de junio en Juárez
    expect(formatoFechaHora('2026-07-01T05:30:00Z')).toBe('30 jun 2026, 23:30')
  })

  it('muestra la hora local del ejemplo del contrato', () => {
    expect(formatoFechaHora('2026-11-24T21:05:00Z')).toBe('24 nov 2026, 14:05')
  })

  it('una fecha sin hora (fecha_reparacion) no retrocede un día', () => {
    expect(formatoFecha('2026-11-20')).toBe('20 nov 2026')
  })

  it('devuelve una raya si no hay fecha o es inválida', () => {
    expect(formatoFecha(null)).toBe('—')
    expect(formatoFecha('no es fecha')).toBe('—')
    expect(formatoFechaHora(undefined)).toBe('—')
  })
})

describe('diasDesde', () => {
  it('cuenta días de calendario en Juárez, no bloques de 24 horas', () => {
    // Reporte de las 19:30 del 23 de noviembre (Juárez); son las 08:00 del 24 en Juárez: ya cambió de día
    const ahora = new Date('2026-11-24T15:00:00Z')
    expect(diasDesde('2026-11-24T02:30:00Z', ahora)).toBe(1)
  })

  it('es 0 el mismo día y nunca es negativo', () => {
    const ahora = new Date('2026-11-24T21:00:00Z')
    expect(diasDesde('2026-11-24T18:00:00Z', ahora)).toBe(0)
    expect(diasDesde('2026-11-30T18:00:00Z', ahora)).toBe(0)
  })

  it('cuenta varios días', () => {
    expect(diasDesde('2026-11-19T18:00:00Z', new Date('2026-11-24T18:00:00Z'))).toBe(5)
  })
})
