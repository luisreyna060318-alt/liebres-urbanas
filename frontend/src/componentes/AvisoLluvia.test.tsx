import { act, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { AvisoLluvia as Aviso } from '../api/tipos.ts'
import { simularApi } from '../pruebas/ayudas.tsx'
import AvisoLluvia from './AvisoLluvia.tsx'

const CON_LLUVIA: Aviso = {
  disponible: true,
  hay_aviso: true,
  probabilidad_max_pct: 45,
  horas: 12,
  umbral_pct: 30,
  consultado_en: '2026-11-25T21:30:00Z',
}
const SIN_LLUVIA: Aviso = { ...CON_LLUVIA, hay_aviso: false, probabilidad_max_pct: 10 }
const NO_DISPONIBLE: Aviso = {
  disponible: false,
  hay_aviso: false,
  probabilidad_max_pct: null,
  horas: 12,
  umbral_pct: 30,
  consultado_en: null,
}

function mostrar() {
  return render(
    <MemoryRouter>
      <AvisoLluvia />
    </MemoryRouter>,
  )
}

describe('aviso de lluvia (HU-08.1)', () => {
  it('con probabilidad de lluvia muestra el aviso accesible con la probabilidad máxima', async () => {
    simularApi({ 'GET /api/clima/aviso': { cuerpo: CON_LLUVIA } })
    mostrar()
    const franja = await screen.findByRole('status')
    expect(franja).toHaveTextContent('Posible lluvia en las próximas 12 horas (probabilidad máxima de 45 %)')
    expect(franja).toHaveTextContent('Revisa cómo está tu zona antes de salir')
    expect(screen.queryByText('Pronóstico no disponible')).not.toBeInTheDocument()
  })

  it('el aviso enlaza a la pantalla de la zona', async () => {
    simularApi({ 'GET /api/clima/aviso': { cuerpo: CON_LLUVIA } })
    mostrar()
    expect(await screen.findByRole('link', { name: 'Ver cómo está mi zona' })).toHaveAttribute('href', '/zona')
  })

  it('sin lluvia no muestra nada (CA2)', async () => {
    const api = simularApi({ 'GET /api/clima/aviso': { cuerpo: SIN_LLUVIA } })
    const { container } = mostrar()
    await vi.waitFor(() => expect(api.de('GET /api/clima/aviso')).toHaveLength(1))
    // Se deja pasar el tiempo para que la respuesta llegue y se procese; después no debe haber quedado nada en pantalla
    await act(() => new Promise((resolver) => setTimeout(resolver, 50)))
    expect(container).toBeEmptyDOMElement()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(screen.queryByText('Pronóstico no disponible')).not.toBeInTheDocument()
  })

  it('si el servicio no está disponible muestra "Pronóstico no disponible" sin alarma (CA4)', async () => {
    simularApi({ 'GET /api/clima/aviso': { cuerpo: NO_DISPONIBLE } })
    mostrar()
    expect(await screen.findByText('Pronóstico no disponible')).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it.each([
    ['no hay conexión', 'sin_red' as const],
    ['el servidor responde un error', { status: 500, cuerpo: { detail: 'Error', codigo: 'ERROR' } }],
  ])('si la petición falla (%s) también muestra "Pronóstico no disponible"', async (_caso, respuesta) => {
    simularApi({ 'GET /api/clima/aviso': respuesta })
    mostrar()
    expect(await screen.findByText('Pronóstico no disponible')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('mientras carga no muestra nada', () => {
    simularApi({ 'GET /api/clima/aviso': { cuerpo: CON_LLUVIA } })
    const { container } = mostrar()
    expect(container).toBeEmptyDOMElement()
  })
})
