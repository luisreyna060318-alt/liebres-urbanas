// Utilidades de la gráfica de reportes por semana (componentes/GraficaSemanal.tsx)
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

// "2026-09-07" -> "7 sep". Se lee el texto tal cual: es un día del calendario de Juárez, sin hora ni zona.
export function etiquetaSemana(inicio: string): string {
  const [, mes, dia] = inicio.split('-').map(Number)
  return `${dia} ${MESES[mes - 1]}`
}

// Tope "redondo" del eje: 7 -> 10, 23 -> 50, 120 -> 200. Con 0 reportes el tope es 1 para no dividir entre 0.
export function topeEscala(maximo: number): number {
  if (maximo <= 0) return 1
  const potencia = 10 ** Math.floor(Math.log10(maximo))
  for (const paso of [1, 2, 5, 10]) {
    if (paso * potencia >= maximo) return paso * potencia
  }
  return 10 * potencia
}
