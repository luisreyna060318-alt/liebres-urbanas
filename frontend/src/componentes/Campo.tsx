// Un campo de formulario: etiqueta + control (input, select o textarea) + ayuda + mensaje de error.
// La etiqueta se une al control con htmlFor/id; la ayuda y el error se asocian con aria-describedby,
// y aria-invalid avisa al lector de pantalla que el valor no es válido.
import type { ReactNode } from 'react'

export interface OpcionCampo {
  valor: string
  etiqueta: string
}

interface Props {
  id: string
  etiqueta: ReactNode
  valor: string
  onCambio: (valor: string) => void
  tipo?: 'text' | 'email' | 'password' | 'date' | 'select' | 'textarea'
  opciones?: OpcionCampo[] // solo para tipo "select"
  textoOpcionVacia?: string // primera opción del select (valor ""), por ejemplo "Elige…" o "Todas"
  error?: string
  ayuda?: string
  autoComplete?: string
  maxLength?: number
  filas?: number // solo para tipo "textarea"
  requerido?: boolean
  modoEntrada?: 'text' | 'decimal' | 'numeric' // teclado que se abre en el celular (por ejemplo "decimal" para coordenadas)
  minimo?: string // solo para tipo "date": primera fecha permitida (AAAA-MM-DD)
  maximo?: string // solo para tipo "date": última fecha permitida (AAAA-MM-DD)
  alPresionarEnter?: () => void // en campos de texto: ejecuta una acción (como "Buscar") en vez de enviar el formulario
}

export default function Campo({
  id,
  etiqueta,
  valor,
  onCambio,
  tipo = 'text',
  opciones = [],
  textoOpcionVacia = 'Elige…',
  error,
  ayuda,
  autoComplete,
  maxLength,
  filas = 4,
  requerido = false,
  modoEntrada,
  minimo,
  maximo,
  alPresionarEnter,
}: Props) {
  // Ids de los textos de apoyo, para que el lector de pantalla los lea junto con el campo
  const idAyuda = `${id}-ayuda`
  const idError = `${id}-error`
  const describedBy = [ayuda ? idAyuda : '', error ? idError : ''].filter(Boolean).join(' ') || undefined

  // Atributos que comparten los tres tipos de control
  const comunes = {
    id,
    value: valor,
    'aria-invalid': error ? true : undefined,
    'aria-describedby': describedBy,
    'aria-required': requerido ? true : undefined,
  } as const

  return (
    <div className="campo">
      <label htmlFor={id}>
        {etiqueta}
        {requerido && <span aria-hidden="true"> *</span>}
      </label>

      {tipo === 'select' && (
        <select {...comunes} onChange={(e) => onCambio(e.target.value)}>
          <option value="">{textoOpcionVacia}</option>
          {opciones.map((o) => (
            <option key={o.valor} value={o.valor}>
              {o.etiqueta}
            </option>
          ))}
        </select>
      )}

      {tipo === 'textarea' && (
        <textarea {...comunes} rows={filas} maxLength={maxLength} onChange={(e) => onCambio(e.target.value)} />
      )}

      {tipo !== 'select' && tipo !== 'textarea' && (
        <input
          {...comunes}
          type={tipo}
          autoComplete={autoComplete}
          maxLength={maxLength}
          inputMode={modoEntrada}
          min={minimo}
          max={maximo}
          onChange={(e) => onCambio(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && alPresionarEnter) {
              e.preventDefault() // sin esto, Enter enviaría todo el formulario que contiene al campo
              alPresionarEnter()
            }
          }}
        />
      )}

      {ayuda && (
        <p id={idAyuda} className="campo-ayuda">
          {ayuda}
        </p>
      )}
      {error && (
        <p id={idError} className="campo-error">
          <span aria-hidden="true">⚠ </span>
          {error}
        </p>
      )}
    </div>
  )
}
