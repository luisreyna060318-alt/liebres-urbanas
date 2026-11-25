// Pantalla que aparece al terminar el flujo de /reportar:
//   - modo "creado": el reporte se registró (201). Muestra el folio, la fecha y hora en hora de Juárez y el estado.
//   - modo "confirmado": la persona confirmó un reporte que ya existía; no se creó un folio nuevo.
import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import type { ReportePublico } from '../api/tipos.ts'
import { formatoFechaHora } from '../utils/fechas.ts'
import { ETIQUETA_CATEGORIA, ETIQUETA_ESTADO, ICONO_CATEGORIA } from '../utils/etiquetas.ts'
import Alerta from './Alerta.tsx'

interface Props {
  modo: 'creado' | 'confirmado'
  reporte: ReportePublico
  alReportarOtro: () => void // reinicia la pantalla de /reportar
}

export default function ConfirmacionReporte({ modo, reporte, alReportarOtro }: Props) {
  // El foco pasa al título para que el lector de pantalla anuncie el resultado del envío
  const titulo = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    titulo.current?.focus()
  }, [])

  const creado = modo === 'creado'

  return (
    <section className="confirmacion-reporte">
      <h1 ref={titulo} tabIndex={-1}>
        {creado ? 'Reporte enviado' : 'Gracias por confirmar'}
      </h1>

      {creado ? (
        <Alerta tipo="exito">
          Tu reporte quedó registrado. Guarda el folio para darle seguimiento.
        </Alerta>
      ) : (
        <Alerta tipo="exito">
          Confirmaste el reporte {reporte.folio}. No se creó un folio nuevo: tu aviso se sumó al que ya existe.
        </Alerta>
      )}

      <dl className="datos-reporte">
        <div>
          <dt>Folio</dt>
          <dd className="folio-grande">{reporte.folio}</dd>
        </div>
        <div>
          <dt>Tipo</dt>
          <dd>
            <span aria-hidden="true">{ICONO_CATEGORIA[reporte.categoria]} </span>
            {ETIQUETA_CATEGORIA[reporte.categoria]}
          </dd>
        </div>
        <div>
          <dt>Ubicación</dt>
          <dd>
            {reporte.calle}, {reporte.colonia.nombre}
          </dd>
        </div>
        {creado && (
          <div>
            <dt>Fecha y hora</dt>
            <dd>{formatoFechaHora(reporte.creado_en)} (hora de Ciudad Juárez)</dd>
          </div>
        )}
        <div>
          <dt>Estado</dt>
          <dd>{ETIQUETA_ESTADO[reporte.estado]}</dd>
        </div>
        {creado && reporte.vigente_hasta && (
          <div>
            <dt>Vigente hasta</dt>
            <dd>{formatoFechaHora(reporte.vigente_hasta)} (hora de Ciudad Juárez)</dd>
          </div>
        )}
        {!creado && (
          <div>
            <dt>Confirmaciones</dt>
            <dd>{reporte.confirmaciones}</dd>
          </div>
        )}
      </dl>

      <p className="confirmacion-enlaces">
        <Link to="/mis-reportes" className="boton">
          Ir a Mis reportes
        </Link>
        <Link to="/reportar" className="boton boton-secundario" onClick={alReportarOtro}>
          Reportar otro
        </Link>
      </p>
    </section>
  )
}
