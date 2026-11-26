import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import App from './App.tsx'
import { AuthProvider } from './context/AuthProvider.tsx'
import { CIUDADANO, COORDINADOR, simularApi } from './pruebas/ayudas.tsx'

// Recorrido de la demo con la sesión real: sale la persona ciudadana desde una pantalla suya y entra la coordinadora
const sesion = (usuario: typeof CIUDADANO) => ({
  cuerpo: { access_token: `token-${usuario.id}`, token_type: 'bearer', expira_en_min: 30, usuario },
})

describe('cerrar sesión y entrar con otra cuenta', () => {
  it('quien entra después no cae en "No tienes permiso"', async () => {
    simularApi({
      'POST /api/auth/login': [sesion(CIUDADANO), sesion(COORDINADOR)],
      'GET /api/mis-reportes': { cuerpo: { items: [], total: 0, pagina: 1, tam: 10 } },
    })
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/mis-reportes']}>
          <App />
        </MemoryRouter>
      </AuthProvider>,
    )
    const u = userEvent.setup()
    async function entrar(correo: string) {
      await u.type(screen.getByLabelText(/Correo electrónico/), correo)
      await u.type(screen.getByLabelText(/Contraseña/), 'Segura123')
      await u.click(screen.getByRole('button', { name: 'Entrar' }))
    }

    // Sin sesión se pide entrar y después se vuelve a la pantalla que quería
    await entrar(CIUDADANO.correo)
    expect(await screen.findByRole('heading', { level: 1, name: 'Mis reportes' })).toBeInTheDocument()

    await u.click(screen.getByRole('button', { name: 'Salir' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Iniciar sesión' })).toBeInTheDocument()
    expect(screen.queryByText(/continuar con lo que estabas haciendo/)).not.toBeInTheDocument()

    await entrar(COORDINADOR.correo)
    expect(await screen.findByRole('heading', { level: 1, name: 'Reportes' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'No tienes permiso' })).not.toBeInTheDocument()
  })
})
