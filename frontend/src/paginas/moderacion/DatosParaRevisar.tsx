// Lo que el moderador necesita leer para decidir: descripción, severidad y confirmaciones de otras personas.
import type { ReportePublico } from '../../api/tipos.ts'
import { ETIQUETA_PROFUNDIDAD } from '../../utils/etiquetas.ts'

export default function DatosParaRevisar({ reporte }: { reporte: ReportePublico }) {
  return (
    <>
      {reporte.descripcion && <p className="moderacion-descripcion">Descripción: {reporte.descripcion}</p>}
      <p className="tarjeta-reporte-detalle">
        {reporte.severidad && `Severidad: ${ETIQUETA_PROFUNDIDAD[reporte.severidad]} · `}
        {reporte.confirmaciones} {reporte.confirmaciones === 1 ? 'confirmación' : 'confirmaciones'}
      </p>
    </>
  )
}
