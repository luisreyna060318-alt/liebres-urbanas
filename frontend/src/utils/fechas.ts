// Fechas y horas. El servidor manda ISO 8601 en UTC (con Z); la persona las ve en la hora de Ciudad Juárez (RN-02).
// Sin esta conversión, un reporte hecho a las 8 p. m. en Juárez aparecería con la fecha del día siguiente.

export const ZONA_HORARIA = 'America/Ciudad_Juarez'
const LOCALE = 'es-MX'
const SIN_DATO = '—'

const formatoDia = new Intl.DateTimeFormat(LOCALE, {
  timeZone: ZONA_HORARIA,
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})

const formatoDiaHora = new Intl.DateTimeFormat(LOCALE, {
  timeZone: ZONA_HORARIA,
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23', // 24 horas: no hay confusión con a. m. y p. m.
})

// Fecha sin hora (por ejemplo fecha_reparacion: "2026-11-20"): es un día del calendario, no un instante.
// Se muestra en UTC para que no retroceda un día al convertirla a la hora de Juárez.
const formatoDiaCalendario = new Intl.DateTimeFormat(LOCALE, {
  timeZone: 'UTC',
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})

const SOLO_FECHA = /^\d{4}-\d{2}-\d{2}$/

function aFecha(iso: string): Date | null {
  const fecha = new Date(iso)
  return Number.isNaN(fecha.getTime()) ? null : fecha
}

// "2026-11-24T02:30:00Z" -> "23 nov 2026" (en Juárez todavía es 23 de noviembre)
export function formatoFecha(iso: string | null | undefined): string {
  if (!iso) return SIN_DATO
  const fecha = aFecha(iso)
  if (!fecha) return SIN_DATO
  return (SOLO_FECHA.test(iso) ? formatoDiaCalendario : formatoDia).format(fecha)
}

// "2026-11-24T21:05:00Z" -> "24 nov 2026, 14:05"
export function formatoFechaHora(iso: string | null | undefined): string {
  if (!iso) return SIN_DATO
  const fecha = aFecha(iso)
  if (!fecha) return SIN_DATO
  return formatoDiaHora.format(fecha)
}

// Día del calendario de Juárez como número comparable ("2026-11-23" -> días desde 1970)
function diaEnJuarez(fecha: Date): number {
  const partes = new Intl.DateTimeFormat('en-CA', { timeZone: ZONA_HORARIA, year: 'numeric', month: '2-digit', day: '2-digit' })
    .format(fecha) // "2026-11-23"
    .split('-')
    .map(Number)
  return Date.UTC(partes[0], partes[1] - 1, partes[2]) / 86_400_000
}

// Días de calendario (en Juárez) desde `iso` hasta `ahora`. Un reporte de ayer en la noche tiene 1 día aunque
// no hayan pasado 24 horas. Nunca devuelve negativos.
export function diasDesde(iso: string, ahora: Date = new Date()): number {
  const fecha = aFecha(iso)
  if (!fecha) return 0
  return Math.max(0, Math.round(diaEnJuarez(ahora) - diaEnJuarez(fecha)))
}
