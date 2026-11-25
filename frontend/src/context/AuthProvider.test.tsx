import { act, fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as auth from '../api/auth.ts'
import { leerToken } from '../api/sesion.ts'
import type { SesionRespuesta } from '../api/tipos.ts'
import { CIUDADANO, simularFetch } from '../pruebas/ayudas.tsx'
import { AuthProvider } from './AuthProvider.tsx'
import { useAuth } from './AuthContexto.ts'

vi.mock('../api/auth.ts')

const sesion = (token: string): SesionRespuesta => ({
  access_token: token,
  token_type: 'bearer',
  expira_en_min: 30,
  usuario: CIUDADANO,
})

// Pantalla mínima que muestra lo que expone la sesión
function Panel() {
  const { usuario, aviso, login, tienePermiso } = useAuth()
  return (
    <div>
      <p>Usuario: {usuario?.nombre ?? 'nadie'}</p>
      <p>Aviso: {aviso ?? 'ninguno'}</p>
      <p>Es ciudadano: {tienePermiso(['ciudadano']) ? 'sí' : 'no'}</p>
      <button onClick={() => void login('ana@ejemplo.test', 'Segura123')}>entrar</button>
    </div>
  )
}

async function iniciarSesion() {
  render(
    <AuthProvider>
      <Panel />
    </AuthProvider>,
  )
  await act(async () => {
    fireEvent.click(screen.getByText('entrar'))
  })
}

// Simula una acción de la persona (un clic en cualquier parte)
async function actuar() {
  await act(async () => {
    window.dispatchEvent(new Event('pointerdown'))
  })
}

async function pasar(minutos: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(minutos * 60_000)
  })
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.mocked(auth.iniciarSesion).mockResolvedValue(sesion('token-1'))
  vi.mocked(auth.renovarSesion).mockResolvedValue(sesion('token-nuevo'))
  simularFetch([], { inactividad_min: 30 })
})

describe('AuthProvider', () => {
  it('el login guarda la sesión y tienePermiso usa el rol', async () => {
    await iniciarSesion()

    expect(screen.getByText('Usuario: Ana Pérez')).toBeInTheDocument()
    expect(screen.getByText('Es ciudadano: sí')).toBeInTheDocument()
    expect(leerToken()).toBe('token-1')
    expect(sessionStorage.getItem('liebre-urbana-usuario')).toContain('ana@ejemplo.test')
  })

  it('cierra la sesión con un aviso tras 30 minutos sin actividad', async () => {
    await iniciarSesion()

    await pasar(29)
    expect(screen.getByText('Usuario: Ana Pérez')).toBeInTheDocument()

    await pasar(2)
    expect(screen.getByText('Usuario: nadie')).toBeInTheDocument()
    expect(screen.getByText(/Aviso: Cerramos tu sesión por inactividad/)).toBeInTheDocument()
    expect(leerToken()).toBeNull()
    expect(sessionStorage.getItem('liebre-urbana-token')).toBeNull()
  })

  it('la actividad mantiene la sesión abierta', async () => {
    await iniciarSesion()

    for (let i = 0; i < 4; i++) {
      await pasar(20)
      await actuar()
    }
    expect(screen.getByText('Usuario: Ana Pérez')).toBeInTheDocument()
  })

  it('renueva el token con la actividad, como máximo una vez cada 5 minutos', async () => {
    await iniciarSesion()

    await pasar(2)
    await actuar()
    expect(auth.renovarSesion).not.toHaveBeenCalled() // aún no pasan 5 minutos desde el login

    await pasar(4) // 6 minutos desde el login
    await actuar()
    expect(auth.renovarSesion).toHaveBeenCalledTimes(1)
    expect(leerToken()).toBe('token-nuevo')

    await actuar()
    await actuar()
    expect(auth.renovarSesion).toHaveBeenCalledTimes(1) // sigue siendo una sola

    await pasar(5)
    await actuar()
    expect(auth.renovarSesion).toHaveBeenCalledTimes(2)
  })

  it('usa el tiempo de inactividad que manda GET /api/reglas', async () => {
    simularFetch([], { inactividad_min: 10 })
    await iniciarSesion()

    await pasar(11)
    expect(screen.getByText('Usuario: nadie')).toBeInTheDocument()
  })

  it('un contexto sin proveedor avisa del error de uso', () => {
    function Suelto() {
      useAuth()
      return null
    }
    const consola = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<Suelto />)).toThrow(/AuthProvider/)
    consola.mockRestore()
  })
})
