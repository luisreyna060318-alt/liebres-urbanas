// Una casilla (checkbox) con su texto y su mensaje de error, con las mismas asociaciones de accesibilidad que Campo.
import type { ReactNode } from 'react'

interface Props {
  id: string
  etiqueta: ReactNode // puede incluir un enlace, por ejemplo al aviso de privacidad
  marcada: boolean
  onCambio: (marcada: boolean) => void
  error?: string
}

export default function CampoCasilla({ id, etiqueta, marcada, onCambio, error }: Props) {
  const idError = `${id}-error`

  return (
    <div className="campo campo-casilla">
      <input
        id={id}
        type="checkbox"
        checked={marcada}
        onChange={(e) => onCambio(e.target.checked)}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? idError : undefined}
      />
      <label htmlFor={id}>{etiqueta}</label>
      {error && (
        <p id={idError} className="campo-error">
          <span aria-hidden="true">⚠ </span>
          {error}
        </p>
      )}
    </div>
  )
}
