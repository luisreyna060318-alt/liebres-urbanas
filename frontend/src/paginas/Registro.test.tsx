import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { ErrorApi } from '../api/cliente.ts'
import { authFalso, ConAuth, simularFetch } from '../pruebas/ayudas.tsx'
import type { AuthValor } from '../context/AuthContexto.ts'
import Registro from './Registro.tsx'

function renderizar(auth: AuthValor) {
  return render(
    <ConAuth valor={auth}>
      <MemoryRouter>
        <Registro />
      </MemoryRouter>
    </ConAuth>,
  )
}

async function capturar(nombre: string, correo: string, password: string, acepta: boolean) {
  const u = userEvent.setup()
  if (nombre) await u.type(screen.getByLabelText(/Nombre/), nombre)
  if (correo) await u.type(screen.getByLabelText(/Correo electrónico/), correo)
  if (password) await u.type(screen.getByLabelText(/Contraseña/), password)
  if (acepta) await u.click(screen.getByRole('checkbox'))
  return u
}

beforeEach(() => {
  simularFetch() // la pantalla pide GET /api/reglas para conocer el mínimo de la contraseña
})

describe('Registro', () => {
  it('con el formulario vacío muestra un error junto a cada campo y no llama a la API', async () => {
    const auth = authFalso()
    renderizar(auth)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Crear cuenta' }))

    const nombre = screen.getByLabelText(/Nombre/)
    expect(nombre).toHaveAttribute('aria-invalid', 'true')
    // El mensaje está asociado al campo con aria-describedby
    expect(nombre).toHaveAccessibleDescription(/Escribe tu nombre/)
    expect(screen.getByLabelText(/Correo electrónico/)).toHaveAccessibleDescription(/Escribe tu correo/)
    expect(screen.getByLabelText(/Contraseña/)).toHaveAccessibleDescription(/Escribe una contraseña/)
    expect(screen.getByRole('checkbox')).toHaveAccessibleDescription(/aceptar el aviso de privacidad/)
    expect(auth.registro).not.toHaveBeenCalled()
  })

  it('con una contraseña débil muestra el error y conserva lo capturado', async () => {
    const auth = authFalso()
    renderizar(auth)
    const u = await capturar('Ana Pérez', 'ana@ejemplo.test', 'soloLetras', true)
    await u.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(screen.getByLabelText(/Contraseña/)).toHaveAccessibleDescription(/letras y números/)
    // Nada de lo escrito se borra (HU-01.1 CA3)
    expect(screen.getByLabelText(/Nombre/)).toHaveValue('Ana Pérez')
    expect(screen.getByLabelText(/Correo electrónico/)).toHaveValue('ana@ejemplo.test')
    expect(screen.getByLabelText(/Contraseña/)).toHaveValue('soloLetras')
    expect(screen.getByRole('checkbox')).toBeChecked()
    expect(auth.registro).not.toHaveBeenCalled()
  })

  it('muestra junto al campo los errores que devuelve el servidor y conserva lo capturado', async () => {
    const error = new ErrorApi(422, 'VALIDACION', 'Revisa los datos.', {
      correo: 'Ese correo no es válido para el servidor.',
      password: 'La contraseña es demasiado común.',
    })
    const auth = authFalso({ registro: () => Promise.reject(error) })
    renderizar(auth)
    const u = await capturar('Ana Pérez', 'ana@ejemplo.test', 'Segura123', true)
    await u.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(await screen.findByText('Ese correo no es válido para el servidor.')).toBeInTheDocument()
    expect(screen.getByLabelText(/Correo electrónico/)).toHaveAccessibleDescription(/no es válido para el servidor/)
    expect(screen.getByLabelText(/Contraseña/)).toHaveAccessibleDescription(/demasiado común/)
    expect(screen.getByLabelText(/Nombre/)).toHaveValue('Ana Pérez')
    expect(screen.getByLabelText(/Contraseña/)).toHaveValue('Segura123')
  })

  it('un correo ya registrado (409) se muestra junto al campo de correo', async () => {
    const error = new ErrorApi(409, 'CORREO_REGISTRADO', 'Ya existe una cuenta con ese correo.')
    renderizar(authFalso({ registro: () => Promise.reject(error) }))
    const u = await capturar('Ana Pérez', 'ana@ejemplo.test', 'Segura123', true)
    await u.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(await screen.findByLabelText(/Correo electrónico/)).toHaveAccessibleDescription(/Ya existe una cuenta/)
  })

  it('con datos válidos envía los campos del contrato', async () => {
    const auth = authFalso()
    renderizar(auth)
    const u = await capturar('  Ana Pérez ', 'ana@ejemplo.test', 'Segura123', true)
    await u.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(auth.registro).toHaveBeenCalledWith({
      nombre: 'Ana Pérez',
      correo: 'ana@ejemplo.test',
      password: 'Segura123',
      acepta_privacidad: true,
    })
  })

  it('enlaza al aviso de privacidad', () => {
    renderizar(authFalso())
    expect(screen.getByRole('link', { name: /aviso de privacidad/ })).toHaveAttribute('href', '/privacidad')
  })
})
