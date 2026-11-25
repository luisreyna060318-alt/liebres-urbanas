// Un grupo de opciones excluyentes (radio) con su pregunta, ayuda y mensaje de error.
// Se usa cuando conviene ver todas las opciones a la vez: ¿está señalizado?, ¿hay riesgo?, ¿qué quieres reportar?
// El fieldset recibe el foco si hay un error (tabIndex -1), y el error se asocia con aria-describedby.
import type { ReactNode } from 'react'

export interface OpcionRadio {
  valor: string
  etiqueta: ReactNode
  deshabilitada?: boolean
}

interface Props {
  id: string // también es el `name` de los radios; los radios usan `${id}-${valor}`
  leyenda: ReactNode
  opciones: OpcionRadio[]
  valor: string
  onCambio: (valor: string) => void
  error?: string
  ayuda?: string
  requerido?: boolean
}

export default function GrupoRadios({ id, leyenda, opciones, valor, onCambio, error, ayuda, requerido = false }: Props) {
  const idAyuda = `${id}-ayuda`
  const idError = `${id}-error`
  const describedBy = [ayuda ? idAyuda : '', error ? idError : ''].filter(Boolean).join(' ') || undefined

  return (
    <fieldset id={id} className="grupo-radios" tabIndex={-1} aria-describedby={describedBy}>
      <legend>
        {leyenda}
        {requerido && <span aria-hidden="true"> *</span>}
      </legend>

      {ayuda && (
        <p id={idAyuda} className="campo-ayuda">
          {ayuda}
        </p>
      )}

      {opciones.map((opcion) => (
        <div className="opcion-radio" key={opcion.valor}>
          <input
            type="radio"
            id={`${id}-${opcion.valor}`}
            name={id}
            value={opcion.valor}
            checked={valor === opcion.valor}
            disabled={opcion.deshabilitada}
            onChange={() => onCambio(opcion.valor)}
          />
          <label htmlFor={`${id}-${opcion.valor}`}>{opcion.etiqueta}</label>
        </div>
      ))}

      {error && (
        <p id={idError} className="campo-error">
          <span aria-hidden="true">⚠ </span>
          {error}
        </p>
      )}
    </fieldset>
  )
}
