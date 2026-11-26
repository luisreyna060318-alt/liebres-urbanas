// Formulario para rechazar un reporte (HU-05.1): motivo obligatorio y, si el motivo lo pide ("Otro"),
// una explicación obligatoria para quien reportó. El servidor repite las mismas validaciones (422 por campo).
import { useState } from 'react'
import type { FormEvent } from 'react'
import { ErrorApi } from '../../api/cliente.ts'
import { rechazarReporte } from '../../api/moderacion.ts'
import type { MotivoRechazo } from '../../api/tipos.ts'
import Alerta from '../../componentes/Alerta.tsx'
import Boton from '../../componentes/Boton.tsx'
import Campo from '../../componentes/Campo.tsx'
import { useFocoAlMontar } from '../../hooks/useFocoAlMontar.ts'
import { useReglas } from '../../hooks/useReglas.ts'
import { estaDesfasado } from './acciones.ts'
import type { PropsAccion } from './acciones.ts'

interface Props extends PropsAccion {
  motivos: MotivoRechazo[]
}

export default function FormularioRechazo({ reporte, motivos, alTerminar, alDesfasarse, alCancelar }: Props) {
  const formulario = useFocoAlMontar<HTMLFormElement>() // el botón que abrió el formulario ya no está
  // Límite propio del comentario (COMENTARIO_MAX en el backend), tomado de GET /api/reglas
  const { comentario_max } = useReglas()
  const [motivoId, setMotivoId] = useState('')
  const [explicacion, setExplicacion] = useState('')
  const [comentario, setComentario] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [campos, setCampos] = useState<Record<string, string>>({})

  const motivo = motivos.find((m) => String(m.id) === motivoId)
  const pideExplicacion = motivo?.pide_explicacion ?? false
  const id = (campo: string) => `${campo}-${reporte.id}`

  // Las mismas reglas que el servidor, para avisar antes de enviar
  function validarEnCliente(): Record<string, string> {
    const errores: Record<string, string> = {}
    if (!motivo) errores.motivo_rechazo_id = 'Elige un motivo de la lista'
    else if (pideExplicacion && !explicacion.trim()) errores.motivo_texto = `Explica el motivo «${motivo.nombre}»`
    return errores
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setError('')
    const errores = validarEnCliente()
    setCampos(errores)
    if (Object.keys(errores).length > 0 || !motivo) return

    setEnviando(true)
    try {
      await rechazarReporte(reporte.id, {
        motivo_rechazo_id: motivo.id,
        motivo_texto: explicacion.trim() || undefined,
        comentario: comentario.trim() || undefined,
      })
      alTerminar(`Se rechazó el reporte ${reporte.folio} (motivo: ${motivo.nombre}). Quien lo reportó verá el motivo.`)
    } catch (e) {
      if (estaDesfasado(e)) return alDesfasarse(e.detail)
      setError(e instanceof Error ? e.message : 'No se pudo rechazar el reporte.')
      if (e instanceof ErrorApi) setCampos(e.campos)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form ref={formulario} className="formulario-moderacion" onSubmit={(e) => void enviar(e)} aria-label={`Rechazar ${reporte.folio}`} noValidate>
      <Campo
        id={id('motivo')}
        etiqueta="Motivo del rechazo"
        tipo="select"
        requerido
        valor={motivoId}
        onCambio={setMotivoId}
        opciones={motivos.map((m) => ({ valor: String(m.id), etiqueta: m.nombre }))}
        error={campos.motivo_rechazo_id}
      />
      <Campo
        id={id('explicacion')}
        etiqueta={pideExplicacion ? 'Explicación para quien reportó' : 'Explicación para quien reportó (opcional)'}
        tipo="textarea"
        filas={2}
        requerido={pideExplicacion}
        valor={explicacion}
        onCambio={setExplicacion}
        maxLength={comentario_max}
        error={campos.motivo_texto}
        ayuda={pideExplicacion ? 'Este motivo necesita una explicación.' : undefined}
      />
      <Campo
        id={id('comentario-rechazo')}
        etiqueta="Comentario (opcional, público)"
        tipo="textarea"
        filas={2}
        valor={comentario}
        onCambio={setComentario}
        maxLength={comentario_max}
        error={campos.comentario}
        ayuda="Aparece en el historial del reporte."
      />
      {error && <Alerta tipo="error">{error}</Alerta>}
      <div className="formulario-moderacion-botones">
        <Boton type="submit" variante="peligro" cargando={enviando} textoCargando="Rechazando…">
          Confirmar rechazo
        </Boton>
        <Boton variante="secundario" onClick={alCancelar} disabled={enviando}>
          Cancelar
        </Boton>
      </div>
    </form>
  )
}
