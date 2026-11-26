import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import type { UsuarioPublico } from '../api/tipos.ts'
import { authFalso, CIUDADANO, ConAuth, COORDINADOR, MODERADOR, simularApi } from '../pruebas/ayudas.tsx'
import Layout from './Layout.tsx'

// El Layout pide el aviso de lluvia: en estas pruebas el pronóstico dice que no habrá lluvia
beforeEach(() => {
  simularApi({
    'GET /api/clima/aviso': {
      cuerpo: { disponible: true, hay_aviso: false, probabilidad_max_pct: 5, horas: 12, umbral_pct: 30, consultado_en: null },
    },
  })
})

// Devuelve los textos de los enlaces del menú principal
function menuPara(usuario: UsuarioPublico | null): string[] {
  render(
    <ConAuth valor={authFalso({ usuario })}>
      <MemoryRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<p>Inicio</p>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </ConAuth>,
  )
  const menu = screen.getByRole('navigation', { name: 'Principal' })
  return within(menu)
    .getAllByRole('link')
    .map((enlace) => enlace.textContent ?? '')
}

describe('menú por rol (HU-01.3 CA1)', () => {
  it('el ciudadano no ve opciones de moderación ni de administración', () => {
    const enlaces = menuPara(CIUDADANO)
    expect(enlaces).toEqual(expect.arrayContaining(['Reportar', 'Mis reportes']))
    expect(enlaces).not.toContain('Moderación')
    expect(enlaces).not.toContain('Colonias')
    expect(enlaces).not.toContain('Usuarios')
    expect(enlaces).not.toContain('Tablero')
    expect(enlaces).not.toContain('Iniciar sesión')
  })

  it('el moderador ve Moderación y no ve administración ni reportar', () => {
    const enlaces = menuPara(MODERADOR)
    expect(enlaces).toContain('Moderación')
    expect(enlaces).not.toContain('Usuarios')
    expect(enlaces).not.toContain('Reportar')
  })

  it('el coordinador ve moderación (para el avance), colonias, usuarios y tablero', () => {
    const enlaces = menuPara(COORDINADOR)
    expect(enlaces).toEqual(expect.arrayContaining(['Moderación', 'Colonias', 'Usuarios', 'Tablero']))
    expect(enlaces).not.toContain('Reportar')
  })

  it('sin sesión solo se ofrece lo público, iniciar sesión y crear cuenta', () => {
    const enlaces = menuPara(null)
    expect(enlaces).toEqual(['Reportes', '¿Cómo está mi zona?', 'Iniciar sesión', 'Crear cuenta'])
  })

  it('no ofrece las pantallas provisionales (mapa y perfil)', () => {
    const enlaces = menuPara(CIUDADANO)
    expect(enlaces).not.toContain('Mapa')
    expect(enlaces).not.toContain('Mi perfil')
  })
})

describe('estructura semántica del Layout', () => {
  it('tiene header, main, footer con aviso de privacidad y el enlace "Saltar al contenido"', async () => {
    const auth = authFalso({ usuario: CIUDADANO })
    render(
      <ConAuth valor={auth}>
        <MemoryRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<h1>Inicio</h1>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </ConAuth>,
    )
    expect(screen.getByRole('banner')).toHaveTextContent('Liebre Urbana')
    expect(screen.getByRole('main')).toHaveAttribute('id', 'contenido')
    expect(within(screen.getByRole('contentinfo')).getByRole('link', { name: 'Aviso de privacidad' })).toHaveAttribute(
      'href',
      '/privacidad',
    )
    expect(screen.getByRole('link', { name: 'Saltar al contenido' })).toHaveAttribute('href', '#contenido')

    // El botón de salir cierra la sesión
    await userEvent.setup().click(screen.getByRole('button', { name: 'Salir' }))
    expect(auth.logout).toHaveBeenCalledTimes(1)
  })

  it('muestra el aviso cuando la sesión caducó', () => {
    render(
      <ConAuth valor={authFalso({ aviso: 'Tu sesión caducó.' })}>
        <MemoryRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<h1>Inicio</h1>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </ConAuth>,
    )
    expect(screen.getByRole('status')).toHaveTextContent('Tu sesión caducó.')
  })
})

describe('aviso de lluvia en el Layout (HU-08.1)', () => {
  it('con probabilidad de lluvia aparece arriba del contenido principal', async () => {
    simularApi({
      'GET /api/clima/aviso': {
        cuerpo: { disponible: true, hay_aviso: true, probabilidad_max_pct: 45, horas: 12, umbral_pct: 30, consultado_en: null },
      },
    })
    render(
      <ConAuth valor={authFalso()}>
        <MemoryRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<h1>Inicio</h1>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </ConAuth>,
    )
    const aviso = await screen.findByRole('status')
    expect(aviso).toHaveTextContent('probabilidad máxima de 45 %')
    // El aviso va antes del <main> en el documento
    expect(aviso.compareDocumentPosition(screen.getByRole('main')) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })
})
