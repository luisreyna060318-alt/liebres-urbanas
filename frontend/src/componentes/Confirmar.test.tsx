import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import Confirmar from './Confirmar.tsx'

function montar(ocupado = false) {
  const alConfirmar = vi.fn()
  const alCancelar = vi.fn()
  render(
    <Confirmar
      etiqueta="Confirmar la eliminación de Ejemplo"
      mensaje="¿Eliminar Ejemplo?"
      textoConfirmar="Sí, eliminar"
      textoCargando="Eliminando…"
      variante="peligro"
      ocupado={ocupado}
      alConfirmar={alConfirmar}
      alCancelar={alCancelar}
    />,
  )
  return { alConfirmar, alCancelar }
}

describe('Confirmar', () => {
  it('muestra la pregunta, pone el foco en Cancelar y avisa lo que se elige', async () => {
    const { alConfirmar, alCancelar } = montar()
    const u = userEvent.setup()

    expect(screen.getByRole('group', { name: 'Confirmar la eliminación de Ejemplo' })).toHaveTextContent('¿Eliminar Ejemplo?')
    expect(screen.getByRole('button', { name: 'Cancelar' })).toHaveFocus()

    await u.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(alCancelar).toHaveBeenCalledOnce()
    await u.click(screen.getByRole('button', { name: 'Sí, eliminar' }))
    expect(alConfirmar).toHaveBeenCalledOnce()
  })

  it('mientras guarda deshabilita ambos botones y muestra el texto de carga', () => {
    montar(true)
    expect(screen.getByRole('button', { name: 'Eliminando…' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled()
  })
})
