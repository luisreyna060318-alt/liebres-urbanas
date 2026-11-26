// Lo que el moderador necesita leer para decidir, además de la tarjeta (que ya trae la severidad): descripción y
// confirmaciones de otras personas.
import type { ReportePublico } from '../../api/tipos.ts'

export default function DatosParaRevisar({ reporte }: { reporte: ReportePublico }) {
  return (
    <>
      {reporte.descripcion && <p className="moderacion-descripcion">Descripción: {reporte.descripcion}</p>}
      <p className="tarjeta-reporte-detalle">
        {reporte.confirmaciones} {reporte.confirmaciones === 1 ? 'confirmación' : 'confirmaciones'}
      </p>
    </>
  )
}
