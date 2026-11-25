import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { ErrorApi } from '../api/cliente.ts'
import { authFalso, ConAuth } from '../pruebas/ayudas.tsx'
import Login from './Login.tsx'

async function enviar(login: () => Promise<void>) {
  const auth = authFalso({ login })
  render(
    <ConAuth valor={auth}>
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    </ConAuth>,
  )
  const u = userEvent.setup()
  await u.type(screen.getByLabelText('Correo electrónico'), 'ana@ejemplo.test')
  await u.type(screen.getByLabelText('Contraseña'), 'Segura123')
  await u.click(screen.getByRole('button', { name: 'Entrar' }))
}

describe('Login', () => {
  it('muestra el mensaje del servidor si las credenciales fallan y no borra lo escrito', async () => {
    await enviar(() => Promise.reject(new ErrorApi(401, 'CREDENCIALES', 'Correo o contraseña incorrectos.')))

    expect(await screen.findByRole('alert')).toHaveTextContent('Correo o contraseña incorrectos.')
    expect(screen.getByLabelText('Correo electrónico')).toHaveValue('ana@ejemplo.test')
  })

  it('si la cuenta está suspendida muestra el mensaje del servidor', async () => {
    await enviar(() => Promise.reject(new ErrorApi(403, 'CUENTA_SUSPENDIDA', 'Tu cuenta está suspendida. Escribe a la asociación.')))

    expect(await screen.findByRole('alert')).toHaveTextContent('Tu cuenta está suspendida')
  })

  it('valida en el cliente antes de llamar a la API', async () => {
    const auth = authFalso()
    render(
      <ConAuth valor={auth}>
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      </ConAuth>,
    )
    await userEvent.setup().click(screen.getByRole('button', { name: 'Entrar' }))

    expect(screen.getByLabelText('Correo electrónico')).toHaveAccessibleDescription(/Escribe tu correo/)
    expect(screen.getByLabelText('Contraseña')).toHaveAccessibleDescription(/Escribe tu contraseña/)
    expect(auth.login).not.toHaveBeenCalled()
  })
})
