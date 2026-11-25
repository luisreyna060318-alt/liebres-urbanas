import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { AuthValor } from '../context/AuthContexto.ts'
import { authFalso, CIUDADANO, ConAuth, MODERADOR, simularApi } from '../pruebas/ayudas.tsx'
import { encharcamientoMio, reporteMio } from '../pruebas/datos.ts'
import AccionesConfirmacion from './AccionesConfirmacion.tsx'

const ENCHARCAMIENTO = encharcamientoMio()
const BACHE = reporteMio({ estado: 'validado', sin_validar: false })

function renderizar(reporte = ENCHARCAMIENTO, auth: AuthValor = authFalso({ usuario: CIUDADANO })) {
  const alActualizar = vi.fn()
  render(
    <ConAuth valor={auth}>
      <MemoryRouter initialEntries={['/reportes/500']}>
        <AccionesConfirmacion reporte={reporte} alActualizar={alActualizar} />
      </MemoryRouter>
    </ConAuth>,
  )
  return alActualizar
}

describe('AccionesConfirmacion (HU-03.3)', () => {
  it('encharcamiento activo: "Sigue ahí" confirma, devuelve el reporte actualizado y muestra fecha y hora', async () => {
    const actualizado = { ...ENCHARCAMIENTO, vigente_hasta: '2026-11-25T09:00:00Z', confirmaciones: 1 }
    const api = simularApi({ 'POST /api/reportes/500/confirmaciones': { status: 201, cuerpo: actualizado } })
    const alActualizar = renderizar()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Sigue ahí' }))

    expect(await screen.findByText(/Registramos que sigue ahí/)).toBeInTheDocument()
    expect(screen.getByText(/hora de Ciudad Juárez/)).toBeInTheDocument()
    expect(api.de('POST /api/reportes/500/confirmaciones')[0].cuerpo).toEqual({ tipo: 'sigue' })
    expect(alActualizar).toHaveBeenCalledWith(actualizado)
    // Ya respondió: no puede volver a responder desde esta pantalla
    expect(screen.getByRole('button', { name: 'Sigue ahí' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Ya no hay agua' })).toBeDisabled()
  })

  it('"Ya no hay agua" manda el tipo ya_no_hay', async () => {
    const api = simularApi({ 'POST /api/reportes/500/confirmaciones': { status: 201, cuerpo: ENCHARCAMIENTO } })
    const alActualizar = renderizar()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Ya no hay agua' }))

    expect(await screen.findByText(/Registramos que ya no hay agua/)).toBeInTheDocument()
    expect(api.de('POST /api/reportes/500/confirmaciones')[0].cuerpo).toEqual({ tipo: 'ya_no_hay' })
    expect(alActualizar).toHaveBeenCalledTimes(1)
  })

  it('bache abierto: solo ofrece "Confirmar que sigue ahí" (tipo confirma)', async () => {
    const api = simularApi({ 'POST /api/reportes/345/confirmaciones': { status: 201, cuerpo: { ...BACHE, confirmaciones: 3 } } })
    renderizar(BACHE)

    expect(screen.queryByRole('button', { name: 'Ya no hay agua' })).not.toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Confirmar que sigue ahí' }))

    expect(await screen.findByText(/Confirmaste este reporte/)).toBeInTheDocument()
    expect(api.de('POST /api/reportes/345/confirmaciones')[0].cuerpo).toEqual({ tipo: 'confirma' })
  })

  it('409 YA_CONFIRMADO: "Ya respondiste sobre este reporte" y los botones se deshabilitan', async () => {
    simularApi({ 'POST /api/reportes/500/confirmaciones': { status: 409, cuerpo: { detail: 'x', codigo: 'YA_CONFIRMADO' } } })
    const alActualizar = renderizar()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Sigue ahí' }))

    expect(await screen.findByText('Ya respondiste sobre este reporte.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sigue ahí' })).toBeDisabled()
    expect(alActualizar).not.toHaveBeenCalled()
  })

  it('403 ES_TU_REPORTE: "No puedes confirmar tu propio reporte"', async () => {
    simularApi({ 'POST /api/reportes/500/confirmaciones': { status: 403, cuerpo: { detail: 'x', codigo: 'ES_TU_REPORTE' } } })
    renderizar()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Ya no hay agua' }))

    expect(await screen.findByText('No puedes confirmar tu propio reporte.')).toBeInTheDocument()
  })

  it('si falla la conexión permite volver a intentar', async () => {
    simularApi({ 'POST /api/reportes/500/confirmaciones': ['sin_red', { status: 201, cuerpo: ENCHARCAMIENTO }] })
    renderizar()
    const u = userEvent.setup()

    await u.click(screen.getByRole('button', { name: 'Sigue ahí' }))
    expect(await screen.findByText(/No se pudo conectar con el servidor/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sigue ahí' })).toBeEnabled()

    await u.click(screen.getByRole('button', { name: 'Sigue ahí' }))
    expect(await screen.findByText(/Registramos que sigue ahí/)).toBeInTheDocument()
  })

  it('sin sesión invita a iniciar sesión y no muestra botones', () => {
    renderizar(ENCHARCAMIENTO, authFalso())

    expect(screen.getByRole('link', { name: 'inicia sesión' })).toHaveAttribute('href', '/login')
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('un moderador no puede confirmar', () => {
    renderizar(ENCHARCAMIENTO, authFalso({ usuario: MODERADOR }))

    expect(screen.getByText(/Solo las cuentas de ciudadano/)).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('no muestra nada si el reporte ya no admite respuestas (histórico o reparado)', () => {
    const { container } = render(
      <ConAuth valor={authFalso({ usuario: CIUDADANO })}>
        <MemoryRouter>
          <AccionesConfirmacion reporte={encharcamientoMio({ estado: 'historico' })} alActualizar={vi.fn()} />
          <AccionesConfirmacion reporte={reporteMio({ estado: 'reparado' })} alActualizar={vi.fn()} />
        </MemoryRouter>
      </ConAuth>,
    )

    expect(container).toBeEmptyDOMElement()
  })
})
