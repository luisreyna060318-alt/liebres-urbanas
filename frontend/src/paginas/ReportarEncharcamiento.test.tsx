import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { authFalso, CIUDADANO, ConAuth, simularApi } from '../pruebas/ayudas.tsx'
import type { RespuestaSimulada } from '../pruebas/ayudas.tsx'
import { COLONIAS, encharcamientoMio, reporteCercano } from '../pruebas/datos.ts'
import Reportar from './Reportar.tsx'

type Usuario = ReturnType<typeof userEvent.setup>

// El formulario de encharcamiento no pide el catálogo de tipos de daño; solo las colonias del selector
const CATALOGOS: Record<string, RespuestaSimulada> = {
  'GET /api/colonias': { cuerpo: { items: COLONIAS, total: 2, pagina: 1, tam: 500 } },
}

function renderizar() {
  return render(
    <ConAuth valor={authFalso({ usuario: CIUDADANO })}>
      <MemoryRouter>
        <Reportar />
      </MemoryRouter>
    </ConAuth>,
  )
}

async function abrirFormulario(u: Usuario) {
  await u.click(screen.getByRole('radio', { name: /Encharcamiento/ }))
  await screen.findByRole('group', { name: 'Nivel del agua' })
}

async function capturarUbicacion(u: Usuario) {
  await u.click(screen.getByRole('button', { name: 'Capturar la ubicación a mano' }))
  await u.type(screen.getByLabelText(/Calle/), 'Av. Tecnológico')
  await u.selectOptions(await screen.findByLabelText(/Colonia/), '12')
  await u.type(screen.getByLabelText(/Latitud/), '31.7001')
  await u.type(screen.getByLabelText(/Longitud/), '-106.4302')
}

const enviar = (u: Usuario) => u.click(screen.getByRole('button', { name: 'Enviar reporte' }))

describe('Reportar un encharcamiento (HU-03.1)', () => {
  it('ofrece los cuatro niveles del agua y no pregunta por riesgo hasta elegir "Intransitable"', async () => {
    simularApi(CATALOGOS)
    renderizar()
    const u = userEvent.setup()
    await abrirFormulario(u)

    const niveles = screen.getByRole('group', { name: 'Nivel del agua' })
    for (const nivel of ['A un lado de la calle', 'Cubre un carril', 'A media llanta', 'Intransitable']) {
      expect(within(niveles).getByRole('radio', { name: nivel })).toBeInTheDocument()
    }
    expect(screen.queryByRole('group', { name: /vehículos varados/ })).not.toBeInTheDocument()

    await u.click(within(niveles).getByRole('radio', { name: 'Cubre un carril' }))
    expect(screen.queryByRole('group', { name: /vehículos varados/ })).not.toBeInTheDocument()

    await u.click(within(niveles).getByRole('radio', { name: 'Intransitable' }))
    expect(screen.getByRole('group', { name: /¿Hay vehículos varados o personas en riesgo\?/ })).toBeInTheDocument()
  })

  it('con el formulario vacío pide el nivel; con "Intransitable" la pregunta de riesgo es obligatoria', async () => {
    const api = simularApi(CATALOGOS)
    renderizar()
    const u = userEvent.setup()
    await abrirFormulario(u)
    await capturarUbicacion(u)

    await enviar(u)
    expect(screen.getByRole('group', { name: 'Nivel del agua' })).toHaveAccessibleDescription(/Elige qué tan alta está el agua/)

    await u.click(screen.getByRole('radio', { name: 'Intransitable' }))
    await enviar(u)
    expect(screen.getByRole('group', { name: /vehículos varados/ })).toHaveAccessibleDescription(/Responde si hay vehículos varados/)
    expect(api.de('POST /api/reportes/encharcamientos')).toHaveLength(0)
  })

  it('envío exitoso: folio ENC, hora de Juárez, estado Activo y "vigente hasta"', async () => {
    const api = simularApi({
      ...CATALOGOS,
      'POST /api/reportes/encharcamientos': { status: 201, cuerpo: encharcamientoMio() },
    })
    renderizar()
    const u = userEvent.setup()
    await abrirFormulario(u)
    await capturarUbicacion(u)
    await u.click(screen.getByRole('radio', { name: 'A media llanta' }))
    await u.type(screen.getByLabelText(/Descripción/), 'Agua junto al puente')
    await enviar(u)

    expect(await screen.findByRole('heading', { name: 'Reporte enviado' })).toBeInTheDocument()
    expect(api.de('POST /api/reportes/encharcamientos')[0].cuerpo).toEqual({
      lat: 31.7001,
      lon: -106.4302,
      calle: 'Av. Tecnológico',
      colonia_id: 12,
      descripcion: 'Agua junto al puente',
      nivel_agua: 'media_llanta',
      hay_riesgo: null,
      forzar: false,
    })
    expect(screen.getByText('ENC-2026-000045')).toBeInTheDocument()
    expect(screen.getByText('Activo')).toBeInTheDocument()
    expect(screen.getByText(/24 nov 2026, 14:05 \(hora de Ciudad Juárez\)/)).toBeInTheDocument()
    expect(screen.getByText(/24 nov 2026, 20:05 \(hora de Ciudad Juárez\)/)).toBeInTheDocument() // vigente hasta
    expect(screen.getByText('Vigente hasta')).toBeInTheDocument()
  })

  it('un encharcamiento intransitable envía la respuesta de riesgo', async () => {
    const api = simularApi({
      ...CATALOGOS,
      'POST /api/reportes/encharcamientos': { status: 201, cuerpo: encharcamientoMio({ nivel_agua: 'intransitable', hay_riesgo: true }) },
    })
    renderizar()
    const u = userEvent.setup()
    await abrirFormulario(u)
    await capturarUbicacion(u)
    await u.click(screen.getByRole('radio', { name: 'Intransitable' }))
    await u.click(screen.getByRole('radio', { name: /Sí, hay vehículos varados/ }))
    await enviar(u)

    await screen.findByRole('heading', { name: 'Reporte enviado' })
    expect(api.de('POST /api/reportes/encharcamientos')[0].cuerpo).toMatchObject({ nivel_agua: 'intransitable', hay_riesgo: true })
  })

  it('si falla la conexión conserva lo capturado', async () => {
    simularApi({ ...CATALOGOS, 'POST /api/reportes/encharcamientos': 'sin_red' })
    renderizar()
    const u = userEvent.setup()
    await abrirFormulario(u)
    await capturarUbicacion(u)
    await u.click(screen.getByRole('radio', { name: 'Cubre un carril' }))
    await enviar(u)

    expect(await screen.findByText(/Tus datos siguen aquí/)).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'Cubre un carril' })).toBeChecked()
    expect(screen.getByLabelText(/Calle/)).toHaveValue('Av. Tecnológico')
  })

  describe('posible duplicado', () => {
    const VIGENTE = reporteCercano({
      id: 88,
      folio: 'ENC-2026-000040',
      categoria: 'encharcamiento',
      estado: 'activo',
      sin_validar: false,
      distancia_m: 30,
      antiguedad_dias: 0,
    })
    const DUPLICADO = {
      status: 409,
      cuerpo: { detail: 'Hay un encharcamiento vigente cerca.', codigo: 'POSIBLE_DUPLICADO', duplicados: [VIGENTE] },
    }

    async function llegarAlAviso(u: Usuario) {
      await abrirFormulario(u)
      await capturarUbicacion(u)
      await u.click(screen.getByRole('radio', { name: 'A un lado de la calle' }))
      await enviar(u)
      return screen.findByRole('region', { name: '¿Es el mismo problema?' })
    }

    it('"Sigue ahí" confirma el existente con tipo sigue y no crea folio', async () => {
      const api = simularApi({
        ...CATALOGOS,
        'POST /api/reportes/encharcamientos': DUPLICADO,
        'POST /api/reportes/88/confirmaciones': { status: 201, cuerpo: encharcamientoMio({ id: 88, folio: 'ENC-2026-000040' }) },
      })
      renderizar()
      const u = userEvent.setup()
      const aviso = await llegarAlAviso(u)

      expect(within(aviso).getByText(/Encharcamiento/)).toBeInTheDocument()
      expect(within(aviso).getByText(/a 30 m/)).toBeInTheDocument()
      await u.click(within(aviso).getByRole('button', { name: /Sigue ahí/ }))

      expect(await screen.findByRole('heading', { name: 'Gracias por confirmar' })).toBeInTheDocument()
      expect(api.de('POST /api/reportes/88/confirmaciones')[0].cuerpo).toEqual({ tipo: 'sigue' })
      expect(api.de('POST /api/reportes/encharcamientos')).toHaveLength(1)
    })

    it('"Reportarlo de todos modos" reenvía con forzar: true', async () => {
      const api = simularApi({
        ...CATALOGOS,
        'POST /api/reportes/encharcamientos': [DUPLICADO, { status: 201, cuerpo: encharcamientoMio({ folio: 'ENC-2026-000046' }) }],
      })
      renderizar()
      const u = userEvent.setup()
      const aviso = await llegarAlAviso(u)
      await u.click(within(aviso).getByRole('button', { name: 'Reportarlo de todos modos' }))

      expect(await screen.findByText('ENC-2026-000046')).toBeInTheDocument()
      const envios = api.de('POST /api/reportes/encharcamientos')
      expect(envios.map((e) => (e.cuerpo as { forzar: boolean }).forzar)).toEqual([false, true])
    })
  })
})
