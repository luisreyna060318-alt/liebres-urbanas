import { useEffect, useRef } from 'react'
import Boton from './Boton.tsx'

interface Props {
  etiqueta: string // nombre del grupo para lectores de pantalla, por ejemplo "Confirmar la eliminación de BCH-2026-000001"
  mensaje: string // la pregunta, por ejemplo "¿Eliminar el reporte BCH-2026-000001?"
  textoConfirmar: string // por ejemplo "Sí, eliminar"
  textoCargando?: string // texto del botón mientras se espera a la API
  variante?: 'primario' | 'peligro' // "peligro" para acciones que no se pueden deshacer
  ocupado: boolean
  alConfirmar: () => void
  alCancelar: () => void
}

// Pregunta antes de aplicar un cambio. Al aparecer pasa el foco a "Cancelar" (la opción segura) para quien usa teclado.
// Lo comparten Mis reportes, Administrar colonias y Administrar usuarios.
export default function Confirmar({
  etiqueta,
  mensaje,
  textoConfirmar,
  textoCargando,
  variante = 'primario',
  ocupado,
  alConfirmar,
  alCancelar,
}: Props) {
  const cancelar = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    cancelar.current?.focus()
  }, [])

  return (
    <div className="confirmar-borrado" role="group" aria-label={etiqueta}>
      <p>{mensaje}</p>
      <Boton variante={variante} onClick={alConfirmar} cargando={ocupado} textoCargando={textoCargando}>
        {textoConfirmar}
      </Boton>
      <button type="button" className="boton boton-secundario" onClick={alCancelar} disabled={ocupado} ref={cancelar}>
        Cancelar
      </button>
    </div>
  )
}
