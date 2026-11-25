import type { ReactNode } from 'react'
import Boton from './Boton.tsx'

interface Props {
  cargando: boolean
  error: string | null
  vacio?: boolean // true cuando la consulta salió bien pero no hay resultados
  textoCargando?: string
  textoVacio?: string // mensaje que invita a la siguiente acción, por ejemplo "Aún no tienes reportes. Crea el primero."
  onReintentar?: () => void
  children?: ReactNode // el contenido real: solo se muestra si no hay carga, error ni vacío
}

// Toda pantalla que consulta la API muestra uno de estos estados: cargando, error (con "Reintentar"), vacío o el contenido
export default function Estado({
  cargando,
  error,
  vacio = false,
  textoCargando = 'Cargando…',
  textoVacio = 'No hay resultados.',
  onReintentar,
  children,
}: Props) {
  if (cargando) {
    return (
      <div className="estado" role="status">
        <p>{textoCargando}</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="estado" role="alert">
        <p>{error}</p>
        {onReintentar && <Boton onClick={onReintentar}>Reintentar</Boton>}
      </div>
    )
  }

  if (vacio) {
    return (
      <div className="estado" role="status">
        <p>{textoVacio}</p>
      </div>
    )
  }

  return <>{children}</>
}
