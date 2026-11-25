import { useEffect } from 'react'

// Cambia el título de la pestaña en cada pantalla (ayuda a la accesibilidad y a quien usa lector de pantalla)
export function useTitulo(titulo: string) {
  useEffect(() => {
    document.title = `${titulo} · Liebre Urbana`
  }, [titulo])
}
