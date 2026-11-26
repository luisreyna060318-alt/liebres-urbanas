// /moderacion (HU-05.1 y HU-05.2). Pestañas accesibles: "Por revisar" (validar o rechazar baches nuevos, solo
// moderador) y "En seguimiento" (registrar el avance de la reparación: moderador y coordinador, RN-05).
// Pestañas con el patrón de WAI-ARIA: las flechas izquierda/derecha cambian de pestaña y Tab entra al panel.
import { useRef, useState } from 'react'
import type { KeyboardEvent, ReactNode } from 'react'
import { useAuth } from '../context/AuthContexto.ts'
import { useTitulo } from '../hooks/useTitulo.ts'
import { ROLES_MODERADOR } from '../utils/menu.ts'
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
  const { tienePermiso } = useAuth()
  // El servidor rechaza la bandeja a quien no es moderador (403): aquí solo se evita mostrarla
  const pestanas = tienePermiso(ROLES_MODERADOR) ? PESTANAS : PESTANAS.filter((p) => p.id === 'seguimiento')
  const [activa, setActiva] = useState(0)
  const botones = useRef<(HTMLButtonElement | null)[]>([])

  function elegir(indice: number) {
    setActiva(indice)
    botones.current[indice]?.focus()
  }

  function alPresionarTecla(evento: KeyboardEvent) {
    const ultima = pestanas.length - 1
    if (evento.key === 'ArrowRight') elegir(activa === ultima ? 0 : activa + 1)
    else if (evento.key === 'ArrowLeft') elegir(activa === 0 ? ultima : activa - 1)
    else if (evento.key === 'Home') elegir(0)
    else if (evento.key === 'End') elegir(ultima)
    else return
    evento.preventDefault()
  }

  const pestana = pestanas[activa]

  return (
    <section>
      <h1>Moderación</h1>
      <div className="pestanas" role="tablist" aria-label="Secciones de moderación" onKeyDown={alPresionarTecla}>
        {pestanas.map((p, i) => (
          <button
            key={p.id}
            ref={(boton) => {
              botones.current[i] = boton
            }}
            type="button"
            role="tab"
            id={`pestana-${p.id}`}
            aria-controls={i === activa ? `panel-${p.id}` : undefined} // solo existe el panel de la pestaña activa
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
