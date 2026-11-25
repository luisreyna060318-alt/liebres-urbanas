import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import Estado from './Estado.tsx'
import Paginacion from './Paginacion.tsx'

describe('Estado', () => {
  it('muestra "Cargando" mientras espera', () => {
    render(<Estado cargando error={null}>contenido</Estado>)
    expect(screen.getByRole('status')).toHaveTextContent('Cargando')
    expect(screen.queryByText('contenido')).not.toBeInTheDocument()
  })

  it('muestra el error con un botón "Reintentar" que vuelve a pedir los datos', async () => {
    const reintentar = vi.fn()
    render(
      <Estado cargando={false} error="No se pudo conectar." onReintentar={reintentar}>
        contenido
      </Estado>,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('No se pudo conectar.')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(reintentar).toHaveBeenCalledTimes(1)
  })

  it('muestra el mensaje de vacío con la siguiente acción', () => {
    render(
      <Estado cargando={false} error={null} vacio textoVacio="Aún no tienes reportes. Crea el primero.">
        contenido
      </Estado>,
    )
    expect(screen.getByText('Aún no tienes reportes. Crea el primero.')).toBeInTheDocument()
  })

  it('con datos muestra el contenido', () => {
    render(
      <Estado cargando={false} error={null}>
        contenido
      </Estado>,
    )
    expect(screen.getByText('contenido')).toBeInTheDocument()
  })
})

describe('Paginacion', () => {
  it('muestra la página y el total, y deshabilita los extremos', async () => {
    const cambiar = vi.fn()
    render(<Paginacion etiqueta="Páginas de prueba" pagina={1} total={25} tam={10} onCambiar={cambiar} />)

    expect(screen.getByText(/Página 1 de 3 \(25 resultados\)/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Anterior' })).toBeDisabled()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(cambiar).toHaveBeenCalledWith(2)
  })
})
