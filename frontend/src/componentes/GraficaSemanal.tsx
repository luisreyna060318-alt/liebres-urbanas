// Gráfica de barras de reportes por semana (HU-07.1), en SVG propio: sin librerías.
// Accesible: role="img" con <title> y <desc>, cada barra lleva su número escrito y abajo hay una tabla con los
// mismos datos. En 360 px la gráfica no se encoge hasta ser ilegible: se desplaza a lo ancho dentro de su caja.
import type { SemanaTablero } from '../api/tipos.ts'
import { etiquetaSemana, topeEscala } from '../utils/grafica.ts'

const ANCHO = 600
const ALTO = 240
const MARGEN = { arriba: 20, derecha: 12, abajo: 36, izquierda: 36 }

interface Props {
  semanas: SemanaTablero[]
}

export default function GraficaSemanal({ semanas }: Props) {
  const tope = topeEscala(Math.max(0, ...semanas.map((s) => s.total)))
  const altoUtil = ALTO - MARGEN.arriba - MARGEN.abajo
  const anchoUtil = ANCHO - MARGEN.izquierda - MARGEN.derecha
  const anchoColumna = anchoUtil / Math.max(semanas.length, 1)
  const y = (valor: number) => MARGEN.arriba + altoUtil - (valor / tope) * altoUtil
  const total = semanas.reduce((suma, s) => suma + s.total, 0)
  const primera = semanas[0]
  const ultima = semanas[semanas.length - 1]
  const resumen = primera
    ? `${total} reportes del ${etiquetaSemana(primera.inicio)} a la semana del ${etiquetaSemana(ultima.inicio)}. ` +
      semanas.map((s) => `Semana del ${etiquetaSemana(s.inicio)}: ${s.total}`).join('; ') + '.'
    : 'Sin datos.'

  return (
    <figure className="grafica-semanal">
      <figcaption>Cada barra es una semana de lunes a domingo (hora de Ciudad Juárez).</figcaption>
      <div className="grafica-desplazable" tabIndex={0} role="region" aria-label="Gráfica de reportes por semana (se desplaza a lo ancho)">
        <svg
          viewBox={`0 0 ${ANCHO} ${ALTO}`}
          role="img"
          aria-labelledby="grafica-semanal-titulo grafica-semanal-desc"
          className="grafica-svg"
        >
          <title id="grafica-semanal-titulo">Reportes creados por semana</title>
          <desc id="grafica-semanal-desc">{resumen}</desc>

          {/* Eje vertical: 0, la mitad y el tope, con líneas guía */}
          {[0, tope / 2, tope].map((valor) => (
            <g key={valor} className="grafica-guia">
              <line x1={MARGEN.izquierda} x2={ANCHO - MARGEN.derecha} y1={y(valor)} y2={y(valor)} />
              <text x={MARGEN.izquierda - 6} y={y(valor) + 4} textAnchor="end">
                {Number.isInteger(valor) ? valor : valor.toFixed(1)}
              </text>
            </g>
          ))}

          {semanas.map((s, i) => {
            const x = MARGEN.izquierda + i * anchoColumna
            const alto = (s.total / tope) * altoUtil
            return (
              <g key={s.inicio} className="grafica-barra">
                <rect x={x + anchoColumna * 0.15} y={y(s.total)} width={anchoColumna * 0.7} height={alto} />
                {/* El número va escrito: la altura de la barra no es la única forma de leer el dato */}
                <text x={x + anchoColumna / 2} y={y(s.total) - 4} textAnchor="middle" className="grafica-valor">
                  {s.total}
                </text>
                <text x={x + anchoColumna / 2} y={ALTO - MARGEN.abajo + 16} textAnchor="middle">
                  {etiquetaSemana(s.inicio)}
                </text>
              </g>
            )
          })}
        </svg>
      </div>

      <table className="tabla-tablero">
        <caption>Reportes por semana (los mismos datos de la gráfica)</caption>
        <thead>
          <tr>
            <th scope="col">Semana que empieza el</th>
            <th scope="col">Reportes</th>
          </tr>
        </thead>
        <tbody>
          {semanas.map((s) => (
            <tr key={s.inicio}>
              <td>{etiquetaSemana(s.inicio)}</td>
              <td>{s.total}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  )
}
