// Resumen de un reporte: folio, tipo (ícono y texto), calle, colonia, estado, antigüedad y, si se conoce, la distancia.
// Sirve para listas y avisos; quien la usa puede agregar botones con `acciones`.
//   <TarjetaReporte reporte={r} acciones={<Boton>Confirmar</Boton>} />
// `mostrarFecha` agrega la fecha y hora del reporte (hora de Juárez); `children` agrega texto extra, como el motivo de rechazo.
// La información nunca depende del color: el tipo y el estado siempre llevan texto.
import type { ReactNode } from 'react'
import type { ReportePublico } from '../api/tipos.ts'
import { formatoFechaHora } from '../utils/fechas.ts'
import { ETIQUETA_CATEGORIA, ETIQUETA_ESTADO, ICONO_CATEGORIA, textoAntiguedad, textoDistancia } from '../utils/etiquetas.ts'

interface Props {
  reporte: ReportePublico & { distancia_m?: number } // ReporteCercano trae la distancia; los demás no
  acciones?: ReactNode
  mostrarFecha?: boolean
  children?: ReactNode
}

export default function TarjetaReporte({ reporte, acciones, mostrarFecha = false, children }: Props) {
  // "Bache", o "Bache · Hundimiento" cuando el daño es de otro tipo
  const subtipo = reporte.categoria === 'bache' && reporte.tipo_dano.codigo !== 'bache' ? ` · ${reporte.tipo_dano.nombre}` : ''

  return (
    <article className="tarjeta tarjeta-reporte">
      <header className="tarjeta-reporte-encabezado">
        <h3 className="tarjeta-reporte-folio">{reporte.folio}</h3>
        <p className="etiqueta-estado">Estado: {ETIQUETA_ESTADO[reporte.estado]}</p>
      </header>

      <p className="tarjeta-reporte-tipo">
        <span aria-hidden="true">{ICONO_CATEGORIA[reporte.categoria]} </span>
        {ETIQUETA_CATEGORIA[reporte.categoria]}
        {subtipo}
        {reporte.sin_validar && <span className="etiqueta-aparte"> (Sin validar)</span>}
      </p>

      <p className="tarjeta-reporte-lugar">
        {reporte.calle}, {reporte.colonia.nombre}
      </p>

      <p className="tarjeta-reporte-detalle">
        {mostrarFecha && `${formatoFechaHora(reporte.creado_en)} · `}
        {textoAntiguedad(reporte.antiguedad_dias)}
        {reporte.distancia_m !== undefined && ` · ${textoDistancia(reporte.distancia_m)}`}
      </p>

      {children}

      {acciones && <div className="tarjeta-reporte-acciones">{acciones}</div>}
    </article>
  )
}
