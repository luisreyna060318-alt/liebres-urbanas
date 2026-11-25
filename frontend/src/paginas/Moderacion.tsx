// /moderacion (solo moderador, HU-05.1 y HU-05.2). Pestañas accesibles: "Por revisar" (validar o rechazar baches
// nuevos) y "En seguimiento" (registrar el avance de la reparación, HU-05.2).
// Pestañas con el patrón de WAI-ARIA: las flechas izquierda/derecha cambian de pestaña y Tab entra al panel.
import { useRef, useState } from 'react'
import type { KeyboardEvent, ReactNode } from 'react'
import { useTitulo } from '../hooks/useTitulo.ts'
import EnSeguimiento from './moderacion/EnSeguimiento.tsx'
import PorRevisar from './moderacion/PorRevisar.tsx'

interface Pestana {
  id: string
  texto: string
  contenido: () => ReactNode
}

const PESTANAS: Pestana[] = [
  { id: 'revisar', texto: 'Por revisar', contenido: () => <PorRevisar /> },
  { id: 'seguimiento', texto: 'En seguimiento', contenido: () => <EnSeguimiento /> },
]

export default function Moderacion() {
  useTitulo('Moderación')
  const [activa, setActiva] = useState(0)
  const botones = useRef<(HTMLButtonElement | null)[]>([])

  function elegir(indice: number) {
    setActiva(indice)
    botones.current[indice]?.focus()
  }

  function alPresionarTecla(evento: KeyboardEvent) {
    const ultima = PESTANAS.length - 1
    if (evento.key === 'ArrowRight') elegir(activa === ultima ? 0 : activa + 1)
    else if (evento.key === 'ArrowLeft') elegir(activa === 0 ? ultima : activa - 1)
    else if (evento.key === 'Home') elegir(0)
    else if (evento.key === 'End') elegir(ultima)
    else return
    evento.preventDefault()
  }

  const pestana = PESTANAS[activa]

  return (
    <section>
      <h1>Moderación</h1>
      <div className="pestanas" role="tablist" aria-label="Secciones de moderación" onKeyDown={alPresionarTecla}>
        {PESTANAS.map((p, i) => (
          <button
            key={p.id}
            ref={(boton) => {
              botones.current[i] = boton
            }}
            type="button"
            role="tab"
            id={`pestana-${p.id}`}
            aria-controls={`panel-${p.id}`}
            aria-selected={i === activa}
            tabIndex={i === activa ? 0 : -1}
            className="pestana"
            onClick={() => setActiva(i)}
          >
            {p.texto}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${pestana.id}`} aria-labelledby={`pestana-${pestana.id}`} className="panel-pestana">
        <h2>{pestana.texto}</h2>
        {pestana.contenido()}
      </div>
    </section>
  )
}
