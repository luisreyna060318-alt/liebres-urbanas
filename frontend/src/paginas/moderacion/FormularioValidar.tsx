// Formulario corto para validar un bache (HU-05.1): comentario público opcional y confirmación.
import { useState } from 'react'
import type { FormEvent } from 'react'
import { ErrorApi } from '../../api/cliente.ts'
import { validarReporte } from '../../api/moderacion.ts'
import Alerta from '../../componentes/Alerta.tsx'
import Boton from '../../componentes/Boton.tsx'
import Campo from '../../componentes/Campo.tsx'
import { useReglas } from '../../hooks/useReglas.ts'
import { estaDesfasado } from './acciones.ts'
import type { PropsAccion } from './acciones.ts'

export default function FormularioValidar({ reporte, alTerminar, alDesfasarse, alCancelar }: PropsAccion) {
  // Límite propio del comentario (COMENTARIO_MAX en el backend), tomado de GET /api/reglas
  const { comentario_max } = useReglas()
  const [comentario, setComentario] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [campos, setCampos] = useState<Record<string, string>>({})

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setEnviando(true)
    setError('')
    setCampos({})
    try {
      await validarReporte(reporte.id, { comentario: comentario.trim() || undefined })
      alTerminar(`Se validó el reporte ${reporte.folio}.`)
    } catch (e) {
      if (estaDesfasado(e)) return alDesfasarse(e.detail)
      setError(e instanceof Error ? e.message : 'No se pudo validar el reporte.')
      if (e instanceof ErrorApi) setCampos(e.campos)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="formulario-moderacion" onSubmit={(e) => void enviar(e)} aria-label={`Validar ${reporte.folio}`} noValidate>
      <Campo
        id={`comentario-validar-${reporte.id}`}
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
        <Boton type="submit" cargando={enviando} textoCargando="Validando…">
          Confirmar validación
        </Boton>
        <Boton variante="secundario" onClick={alCancelar} disabled={enviando}>
          Cancelar
        </Boton>
      </div>
    </form>
  )
}
