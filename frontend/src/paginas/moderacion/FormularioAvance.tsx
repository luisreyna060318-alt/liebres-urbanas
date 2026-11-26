// Formulario para registrar el avance de la reparación (HU-05.2): "En reparación" o "Reparado".
// "Reparado" pide la fecha (máximo hoy y no antes del día del reporte, en la hora de Juárez). El servidor repite la regla.
import { useState } from 'react'
import type { FormEvent } from 'react'
import { ErrorApi } from '../../api/cliente.ts'
import { registrarAvance } from '../../api/moderacion.ts'
import type { EstadoAvance } from '../../api/tipos.ts'
import Alerta from '../../componentes/Alerta.tsx'
import Boton from '../../componentes/Boton.tsx'
import Campo from '../../componentes/Campo.tsx'
import { useReglas } from '../../hooks/useReglas.ts'
import { diaEnJuarez, estaDesfasado } from './acciones.ts'
import type { PropsAccion } from './acciones.ts'

interface Props extends PropsAccion {
  estado: EstadoAvance
}

export default function FormularioAvance({ reporte, estado, alTerminar, alDesfasarse, alCancelar }: Props) {
  // PENDIENTE: el comentario tiene su propio límite (COMENTARIO_MAX en el backend); cuando GET /api/reglas exponga
  // `comentario_max` (otro PR), usarlo aquí. Mientras tanto vale lo mismo que la descripción (500).
  const { descripcion_max } = useReglas()
  // "Hoy" se calcula una vez, al abrir el formulario (no en cada render)
  const [hoy] = useState(() => diaEnJuarez(new Date()))
  const diaReporte = diaEnJuarez(new Date(reporte.creado_en))
  const esReparado = estado === 'reparado'

  const [fecha, setFecha] = useState(hoy)
  const [comentario, setComentario] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [campos, setCampos] = useState<Record<string, string>>({})

  // Las mismas reglas que el servidor; las fechas "AAAA-MM-DD" se comparan bien como texto
  function validarEnCliente(): Record<string, string> {
    if (!esReparado) return {}
    if (!fecha) return { fecha_reparacion: 'Indica la fecha en que se reparó' }
    if (fecha > hoy) return { fecha_reparacion: 'La fecha de reparación no puede ser futura' }
    if (fecha < diaReporte) return { fecha_reparacion: 'La fecha de reparación no puede ser anterior al reporte' }
    return {}
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setError('')
    const errores = validarEnCliente()
    setCampos(errores)
    if (Object.keys(errores).length > 0) return

    setEnviando(true)
    try {
      await registrarAvance(reporte.id, {
        estado,
        comentario: comentario.trim() || undefined,
        fecha_reparacion: esReparado ? fecha : undefined,
      })
      alTerminar(`El reporte ${reporte.folio} quedó como ${esReparado ? 'Reparado' : 'En reparación'}.`)
    } catch (e) {
      if (estaDesfasado(e)) return alDesfasarse(e.detail)
      setError(e instanceof Error ? e.message : 'No se pudo registrar el avance.')
      if (e instanceof ErrorApi) setCampos(e.campos)
    } finally {
      setEnviando(false)
    }
  }

  const idFecha = `fecha-reparacion-${reporte.id}`
  const accion = esReparado ? 'Marcar reparado' : 'Marcar en reparación'

  return (
    <form className="formulario-moderacion" onSubmit={(e) => void enviar(e)} aria-label={`${accion} ${reporte.folio}`} noValidate>
      {esReparado && (
        <Campo
          id={idFecha}
          etiqueta="Fecha de reparación"
          tipo="date"
          valor={fecha}
          onCambio={setFecha}
          minimo={diaReporte}
          maximo={hoy}
          error={campos.fecha_reparacion}
          requerido
        />
      )}
      <Campo
        id={`comentario-avance-${reporte.id}`}
        etiqueta="Comentario (opcional, público)"
        tipo="textarea"
        filas={2}
        valor={comentario}
        onCambio={setComentario}
        maxLength={descripcion_max}
        error={campos.comentario}
        ayuda="Aparece en el historial del reporte."
      />
      {error && <Alerta tipo="error">{error}</Alerta>}
      <div className="formulario-moderacion-botones">
        <Boton type="submit" cargando={enviando} textoCargando="Guardando…">
          Confirmar: {esReparado ? 'Reparado' : 'En reparación'}
        </Boton>
        <Boton variante="secundario" onClick={alCancelar} disabled={enviando}>
          Cancelar
        </Boton>
      </div>
    </form>
  )
}
