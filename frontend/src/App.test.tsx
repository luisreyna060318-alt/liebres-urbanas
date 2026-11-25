import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import App from './App.tsx'
import type { AuthValor } from './context/AuthContexto.ts'
import { authFalso, CIUDADANO, ConAuth, COORDINADOR, simularFetch } from './pruebas/ayudas.tsx'

function irA(ruta: string, auth: AuthValor) {
  return render(
    <ConAuth valor={auth}>
      <MemoryRouter initialEntries={[ruta]}>
        <App />
      </MemoryRouter>
    </ConAuth>,
  )
}

beforeEach(() => {
  simularFetch()
})

describe('rutas de la aplicación', () => {
  it('cada pantalla pública tiene un solo h1', () => {
    for (const ruta of ['/', '/zona', '/mapa', '/reportes/5', '/login', '/registro', '/privacidad', '/no-existe']) {
      const { unmount } = irA(ruta, authFalso())
      expect(screen.getAllByRole('heading', { level: 1 }), ruta).toHaveLength(1)
      unmount()
    }
  })

  it('una ruta que no existe muestra la página 404', () => {
    irA('/no-existe', authFalso())
    expect(screen.getByRole('heading', { level: 1, name: 'Página no encontrada' })).toBeInTheDocument()
  })

  it('el ciudadano no entra a moderación ni a administración', () => {
    for (const ruta of ['/moderacion', '/admin/colonias', '/admin/usuarios', '/tablero']) {
      const { unmount } = irA(ruta, authFalso({ usuario: CIUDADANO }))
      expect(screen.getByRole('heading', { level: 1, name: 'No tienes permiso' }), ruta).toBeInTheDocument()
      unmount()
    }
  })

  it('el ciudadano entra a sus pantallas y el coordinador al tablero', () => {
    const { unmount } = irA('/mis-reportes', authFalso({ usuario: CIUDADANO }))
    expect(screen.getByRole('heading', { level: 1, name: 'Mis reportes' })).toBeInTheDocument()
    unmount()

    irA('/tablero', authFalso({ usuario: COORDINADOR }))
    expect(screen.getByRole('heading', { level: 1, name: 'Tablero de indicadores' })).toBeInTheDocument()
  })

  it('sin sesión, una ruta privada lleva a iniciar sesión', () => {
    irA('/reportar', authFalso())
    expect(screen.getByRole('heading', { level: 1, name: 'Iniciar sesión' })).toBeInTheDocument()
  })

  it('el aviso de privacidad explica los derechos ARCO y que la asociación es ficticia', () => {
    irA('/privacidad', authFalso())
    expect(screen.getByRole('heading', { level: 1, name: 'Aviso de privacidad' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /derechos ARCO/ })).toBeInTheDocument()
    expect(screen.getByText(/ficticia/)).toBeInTheDocument()
  })
})
