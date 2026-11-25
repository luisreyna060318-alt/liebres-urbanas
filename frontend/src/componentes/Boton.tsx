import type { ButtonHTMLAttributes } from 'react'

interface Props extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className'> {
  variante?: 'primario' | 'secundario' | 'peligro'
  cargando?: boolean // deshabilita el botón y muestra `textoCargando` mientras se espera a la API
  textoCargando?: string
}

// Botón con el estilo del proyecto. Por omisión es type="button" para que no envíe formularios sin querer.
export default function Boton({
  variante = 'primario',
  cargando = false,
  textoCargando = 'Un momento…',
  type = 'button',
  disabled,
  children,
  ...resto
}: Props) {
  const clase = variante === 'primario' ? 'boton' : `boton boton-${variante}`

  return (
    <button type={type} className={clase} disabled={disabled || cargando} aria-busy={cargando || undefined} {...resto}>
      {cargando ? textoCargando : children}
    </button>
  )
}
