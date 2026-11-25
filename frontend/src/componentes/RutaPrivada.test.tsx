import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { authFalso, CIUDADANO, ConAuth, MODERADOR } from '../pruebas/ayudas.tsx'
import type { AuthValor } from '../context/AuthContexto.ts'
import RutaPrivada from './RutaPrivada.tsx'

// Pantalla falsa de /login que muestra de dónde venía la persona
function LoginFalso() {
  const estado = useLocation().state as { desde?: string } | null
  return <p>Pantalla de login. Origen: {estado?.desde}</p>
}

function renderizar(auth: AuthValor, ruta = '/reportar?x=1') {
  return render(
    <ConAuth valor={auth}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/login" element={<LoginFalso />} />
          <Route element={<RutaPrivada roles={['ciudadano']} />}>
            <Route path="/reportar" element={<p>Contenido del ciudadano</p>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </ConAuth>,
  )
}

describe('RutaPrivada', () => {
  it('sin sesión redirige a /login y conserva la ruta de origen', () => {
    renderizar(authFalso())
    expect(screen.getByText(/Pantalla de login/)).toHaveTextContent('Origen: /reportar?x=1')
    expect(screen.queryByText('Contenido del ciudadano')).not.toBeInTheDocument()
  })

  it('con un rol insuficiente muestra el aviso "No tienes permiso"', () => {
    renderizar(authFalso({ usuario: MODERADOR }))
    expect(screen.getByRole('heading', { level: 1, name: 'No tienes permiso' })).toBeInTheDocument()
    expect(screen.queryByText('Contenido del ciudadano')).not.toBeInTheDocument()
  })

  it('con el rol correcto muestra el contenido', () => {
    renderizar(authFalso({ usuario: CIUDADANO }))
    expect(screen.getByText('Contenido del ciudadano')).toBeInTheDocument()
  })

  it('mientras se confirma la sesión guardada no redirige todavía', () => {
    renderizar(authFalso({ cargando: true }))
    expect(screen.getByRole('status')).toHaveTextContent('Cargando')
    expect(screen.queryByText(/Pantalla de login/)).not.toBeInTheDocument()
  })
})
