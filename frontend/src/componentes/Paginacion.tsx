import Boton from './Boton.tsx'

interface Props {
  etiqueta: string // nombre de la navegación para lectores de pantalla, por ejemplo "Páginas de mis reportes"
  pagina: number
  total: number // total de resultados que informa el servidor
  tam: number // resultados por página (viene en la respuesta paginada)
  onCambiar: (pagina: number) => void
}

// Botones Anterior / Siguiente con "Página X de Y" y el total de resultados
export default function Paginacion({ etiqueta, pagina, total, tam, onCambiar }: Props) {
  const totalPaginas = Math.max(1, Math.ceil(total / Math.max(1, tam)))

  return (
    <nav className="paginacion" aria-label={etiqueta}>
      <Boton variante="secundario" disabled={pagina <= 1} onClick={() => onCambiar(pagina - 1)}>
        Anterior
      </Boton>
      <p className="paginacion-info">
        Página {pagina} de {totalPaginas} ({total} {total === 1 ? 'resultado' : 'resultados'})
      </p>
      <Boton variante="secundario" disabled={pagina >= totalPaginas} onClick={() => onCambiar(pagina + 1)}>
        Siguiente
      </Boton>
    </nav>
  )
}
