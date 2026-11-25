import { useTitulo } from '../hooks/useTitulo.ts'

interface Props {
  titulo: string
  historia: string // qué historia de usuario completa esta pantalla, por ejemplo "HU-02.5 Consultar y corregir mis reportes"
}

// Pantalla provisional: tiene su ruta y su protección de rol desde ya, y otro PR la reemplaza por la real.
export default function PaginaProxima({ titulo, historia }: Props) {
  useTitulo(titulo)

  return (
    <section className="proximamente">
      <h1>{titulo}</h1>
      <p className="proximamente-etiqueta">Próximamente</p>
      <p>Esta pantalla todavía no está lista. La completa la historia {historia}.</p>
    </section>
  )
}
