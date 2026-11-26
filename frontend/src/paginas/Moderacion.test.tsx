import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import type { MotivoRechazo, ReportePublico } from '../api/tipos.ts'
import { COORDINADOR, authFalso, ConAuth, MODERADOR, simularApi } from '../pruebas/ayudas.tsx'
import type { RespuestaSimulada } from '../pruebas/ayudas.tsx'
import { COLONIAS, reporteCercano, TIPOS_DANO } from '../pruebas/datos.ts'
import Moderacion from './Moderacion.tsx'

function publico(parcial: Partial<ReportePublico>): ReportePublico {
  const { distancia_m: _d, ...reporte } = reporteCercano({ estado: 'recibido', sin_validar: true, confirmaciones: 0 })
  return { ...reporte, ...parcial }
}

const VIEJO = publico({ id: 1, folio: 'BCH-2026-000001', descripcion: 'Hueco frente a la escuela' })
const NUEVO = publico({ id: 2, folio: 'BCH-2026-000002' })
const MOTIVOS: MotivoRechazo[] = [
  { id: 1, codigo: 'duplicado', nombre: 'Duplicado', pide_explicacion: false },
  { id: 5, codigo: 'otro', nombre: 'Otro', pide_explicacion: true },
]

function pagina(items: ReportePublico[], total = items.length, numero = 1): RespuestaSimulada {
  return { cuerpo: { items, total, pagina: numero, tam: 10 } }
}

const CATALOGOS = {
  'GET /api/colonias': { cuerpo: { items: COLONIAS, total: 2, pagina: 1, tam: 500 } },
  'GET /api/tipos-dano': { cuerpo: TIPOS_DANO },
  'GET /api/motivos-rechazo': { cuerpo: MOTIVOS },
}

function renderizar(usuario = MODERADOR) {
  return render(
    <ConAuth valor={authFalso({ usuario })}>
      <MemoryRouter initialEntries={['/moderacion']}>
        <Moderacion />
      </MemoryRouter>
    </ConAuth>,
  )
}

function tarjeta(folio: string) {
  return screen.getByRole('heading', { name: folio }).closest('article')!
}

describe('Moderación: por revisar (HU-05.1)', () => {
  it('muestra la pestaña "Por revisar" y la bandeja en el orden del servidor', async () => {
    simularApi({ ...CATALOGOS, 'GET /api/moderacion/bandeja': pagina([VIEJO, NUEVO]) })
    renderizar()

    expect(screen.getByRole('tab', { name: 'Por revisar' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tabpanel', { name: 'Por revisar' })).toBeInTheDocument()
    await screen.findByRole('heading', { name: 'BCH-2026-000001' })
    const folios = screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)
    expect(folios).toEqual(['BCH-2026-000001', 'BCH-2026-000002'])
    expect(within(tarjeta('BCH-2026-000001')).getByText('Descripción: Hueco frente a la escuela')).toBeInTheDocument()
    expect(within(tarjeta('BCH-2026-000001')).getByText('Estado: Recibido')).toBeInTheDocument()
  })

  it('sin reportes muestra "No hay reportes por revisar"', async () => {
    simularApi({ ...CATALOGOS, 'GET /api/moderacion/bandeja': pagina([], 0) })
    renderizar()
    expect(await screen.findByText('No hay reportes por revisar.')).toBeInTheDocument()
  })

  it('si falla la consulta muestra el error y deja reintentar', async () => {
    simularApi({ ...CATALOGOS, 'GET /api/moderacion/bandeja': ['sin_red', pagina([VIEJO])] })
    renderizar()
    expect(await screen.findByText(/No se pudo conectar con el servidor/)).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByRole('heading', { name: 'BCH-2026-000001' })).toBeInTheDocument()
  })

  it('los filtros de colonia y tipo vuelven a pedir la bandeja desde la página 1', async () => {
    const api = simularApi({ ...CATALOGOS, 'GET /api/moderacion/bandeja': pagina([VIEJO]) })
    renderizar()
    const u = userEvent.setup()
    await screen.findByRole('option', { name: 'Partido Escobedo' })

    await u.selectOptions(screen.getByLabelText('Colonia'), '12')
    await u.selectOptions(screen.getByLabelText('Tipo de daño'), 'grieta')

    const busquedas = api.de('GET /api/moderacion/bandeja').map((l) => l.url.search)
    expect(busquedas.at(-1)).toBe('?colonia_id=12&tipo_dano_codigo=grieta&pagina=1')
  })

  it('validar con comentario llama a la API, confirma la acción y refresca la bandeja', async () => {
    const api = simularApi({
      ...CATALOGOS,
      'GET /api/moderacion/bandeja': [pagina([VIEJO, NUEVO]), pagina([NUEVO])],
      'POST /api/reportes/1/validar': { cuerpo: { ...VIEJO, estado: 'validado', sin_validar: false } },
    })
    renderizar()
    const u = userEvent.setup()

    await u.click(await screen.findByRole('button', { name: 'Validar BCH-2026-000001' }))
    await u.type(screen.getByLabelText(/Comentario/), 'Visto en sitio')
    await u.click(screen.getByRole('button', { name: 'Confirmar validación' }))

    expect(await screen.findByText('Se validó el reporte BCH-2026-000001.')).toBeInTheDocument()
    expect(api.de('POST /api/reportes/1/validar')[0].cuerpo).toEqual({ comentario: 'Visto en sitio' })
    expect(screen.queryByRole('heading', { name: 'BCH-2026-000001' })).not.toBeInTheDocument()
  })

  it('rechazar con "Otro" exige la explicación antes de enviar', async () => {
    const api = simularApi({
      ...CATALOGOS,
      'GET /api/moderacion/bandeja': [pagina([VIEJO]), pagina([], 0)],
      'POST /api/reportes/1/rechazar': { cuerpo: { ...VIEJO, estado: 'rechazado', sin_validar: false } },
    })
    renderizar()
    const u = userEvent.setup()

    await u.click(await screen.findByRole('button', { name: 'Rechazar BCH-2026-000001' }))
    await u.click(await screen.findByRole('button', { name: 'Confirmar rechazo' }))
    expect(screen.getByText('Elige un motivo de la lista')).toBeInTheDocument()

    await u.selectOptions(screen.getByLabelText(/Motivo del rechazo/), '5')
    await u.click(screen.getByRole('button', { name: 'Confirmar rechazo' }))
    expect(screen.getByText('Explica el motivo «Otro»')).toBeInTheDocument()
    expect(api.de('POST /api/reportes/1/rechazar')).toHaveLength(0)

    await u.type(screen.getByLabelText(/Explicación para quien reportó/), 'Es un estacionamiento privado')
    await u.click(screen.getByRole('button', { name: 'Confirmar rechazo' }))

    expect(await screen.findByText(/Se rechazó el reporte BCH-2026-000001 \(motivo: Otro\)/)).toBeInTheDocument()
    expect(api.de('POST /api/reportes/1/rechazar')[0].cuerpo).toEqual({
      motivo_rechazo_id: 5,
      motivo_texto: 'Es un estacionamiento privado',
    })
    expect(await screen.findByText('No hay reportes por revisar.')).toBeInTheDocument()
  })

  it('muestra junto al campo el error que manda el servidor (422)', async () => {
    simularApi({
      ...CATALOGOS,
      'GET /api/moderacion/bandeja': pagina([VIEJO]),
      'POST /api/reportes/1/rechazar': {
        status: 422,
        cuerpo: { detail: 'Revisa los datos marcados', codigo: 'VALIDACION', campos: { motivo_rechazo_id: 'Elige un motivo de la lista' } },
      },
    })
    renderizar()
    const u = userEvent.setup()

    await u.click(await screen.findByRole('button', { name: 'Rechazar BCH-2026-000001' }))
    await u.selectOptions(await screen.findByLabelText(/Motivo del rechazo/), '1')
    await u.click(screen.getByRole('button', { name: 'Confirmar rechazo' }))

    expect(await screen.findByText('Revisa los datos marcados')).toBeInTheDocument()
    expect(screen.getByLabelText(/Motivo del rechazo/)).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByText('Elige un motivo de la lista')).toBeInTheDocument()
  })

  it('si otra persona ya lo revisó (409) avisa y refresca la bandeja', async () => {
    const api = simularApi({
      ...CATALOGOS,
      'GET /api/moderacion/bandeja': [pagina([VIEJO]), pagina([], 0)],
      'POST /api/reportes/1/validar': {
        status: 409,
        cuerpo: { detail: 'El reporte BCH-2026-000001 está en «Validado»', codigo: 'TRANSICION_INVALIDA' },
      },
    })
    renderizar()
    const u = userEvent.setup()

    await u.click(await screen.findByRole('button', { name: 'Validar BCH-2026-000001' }))
    await u.click(screen.getByRole('button', { name: 'Confirmar validación' }))

    expect(await screen.findByText(/está en «Validado»/)).toBeInTheDocument()
    expect(await screen.findByText('No hay reportes por revisar.')).toBeInTheDocument()
    expect(api.de('GET /api/moderacion/bandeja')).toHaveLength(2)
  })
})

describe('Moderación: en seguimiento (HU-05.2)', () => {
  // Creados hace tiempo, para que "hoy" siempre sea una fecha de reparación válida
  const VALIDADO = publico({ id: 10, folio: 'BCH-2026-000010', estado: 'validado', sin_validar: false, creado_en: '2026-01-10T18:00:00Z' })
  const EN_REPARACION = publico({ id: 11, folio: 'BCH-2026-000011', estado: 'en_reparacion', sin_validar: false, creado_en: '2026-01-05T18:00:00Z' })

  async function abrirSeguimiento(rutas: Parameters<typeof simularApi>[0]) {
    const api = simularApi({ ...CATALOGOS, 'GET /api/moderacion/bandeja': pagina([], 0), ...rutas })
    renderizar()
    const u = userEvent.setup()
    await u.click(screen.getByRole('tab', { name: 'En seguimiento' }))
    return { api, u }
  }

  it('solo la pestaña activa apunta a un panel que existe (aria-controls)', async () => {
    simularApi({ ...CATALOGOS, 'GET /api/moderacion/bandeja': pagina([], 0), 'GET /api/moderacion/seguimiento': pagina([], 0) })
    renderizar()
    const u = userEvent.setup()

    const revisar = screen.getByRole('tab', { name: 'Por revisar' })
    const seguimiento = screen.getByRole('tab', { name: 'En seguimiento' })
    expect(revisar).toHaveAttribute('aria-controls', screen.getByRole('tabpanel').id)
    expect(seguimiento).not.toHaveAttribute('aria-controls')

    await u.click(seguimiento)
    expect(seguimiento).toHaveAttribute('aria-controls', screen.getByRole('tabpanel').id)
    expect(revisar).not.toHaveAttribute('aria-controls')
  })

  it('las flechas del teclado cambian de pestaña', async () => {
    simularApi({ ...CATALOGOS, 'GET /api/moderacion/bandeja': pagina([], 0), 'GET /api/moderacion/seguimiento': pagina([], 0) })
    renderizar()
    const u = userEvent.setup()

    screen.getByRole('tab', { name: 'Por revisar' }).focus()
    await u.keyboard('{ArrowRight}')
    const seguimiento = screen.getByRole('tab', { name: 'En seguimiento' })
    expect(seguimiento).toHaveAttribute('aria-selected', 'true')
    expect(seguimiento).toHaveFocus()
    expect(await screen.findByText('No hay baches validados ni en reparación.')).toBeInTheDocument()
  })

  it('cada bache ofrece solo su siguiente paso', async () => {
    await abrirSeguimiento({ 'GET /api/moderacion/seguimiento': pagina([EN_REPARACION, VALIDADO]) })

    expect(await screen.findByRole('button', { name: 'Marcar en reparación BCH-2026-000010' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Marcar reparado BCH-2026-000011' })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /^Marcar/ })).toHaveLength(2)
  })

  it('si falla la consulta muestra el error y deja reintentar', async () => {
    const { u } = await abrirSeguimiento({ 'GET /api/moderacion/seguimiento': ['sin_red', pagina([VALIDADO])] })
    expect(await screen.findByText(/No se pudo conectar con el servidor/)).toBeInTheDocument()
    await u.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByRole('heading', { name: 'BCH-2026-000010' })).toBeInTheDocument()
  })

  it('marcar en reparación envía el comentario público y refresca la lista', async () => {
    const { api, u } = await abrirSeguimiento({
      'GET /api/moderacion/seguimiento': [pagina([VALIDADO]), pagina([{ ...VALIDADO, estado: 'en_reparacion' }])],
      'POST /api/reportes/10/estado': { cuerpo: { ...VALIDADO, estado: 'en_reparacion' } },
    })

    await u.click(await screen.findByRole('button', { name: 'Marcar en reparación BCH-2026-000010' }))
    expect(screen.queryByLabelText(/Fecha de reparación/)).not.toBeInTheDocument()
    await u.type(screen.getByLabelText(/Comentario/), 'Cuadrilla asignada')
    await u.click(screen.getByRole('button', { name: 'Confirmar: En reparación' }))

    expect(await screen.findByText('El reporte BCH-2026-000010 quedó como En reparación.')).toBeInTheDocument()
    expect(api.de('POST /api/reportes/10/estado')[0].cuerpo).toEqual({ estado: 'en_reparacion', comentario: 'Cuadrilla asignada' })
    expect(await screen.findByRole('button', { name: 'Marcar reparado BCH-2026-000010' })).toBeInTheDocument()
  })

  it('marcar reparado pide una fecha que no sea futura (máximo hoy)', async () => {
    const { api, u } = await abrirSeguimiento({
      'GET /api/moderacion/seguimiento': [pagina([EN_REPARACION]), pagina([], 0)],
      'POST /api/reportes/11/estado': { cuerpo: { ...EN_REPARACION, estado: 'reparado' } },
    })

    await u.click(await screen.findByRole('button', { name: 'Marcar reparado BCH-2026-000011' }))
    const fecha = screen.getByLabelText(/Fecha de reparación/)
    const hoy = fecha.getAttribute('max')!
    expect(fecha).toHaveValue(hoy)
    expect(fecha).toHaveAttribute('min', '2026-01-05')

    fireEvent.change(fecha, { target: { value: '2999-01-01' } })
    await u.click(screen.getByRole('button', { name: 'Confirmar: Reparado' }))
    expect(screen.getByText('La fecha de reparación no puede ser futura')).toBeInTheDocument()
    expect(api.de('POST /api/reportes/11/estado')).toHaveLength(0)

    fireEvent.change(fecha, { target: { value: hoy } })
    await u.click(screen.getByRole('button', { name: 'Confirmar: Reparado' }))
    expect(await screen.findByText('El reporte BCH-2026-000011 quedó como Reparado.')).toBeInTheDocument()
    expect(api.de('POST /api/reportes/11/estado')[0].cuerpo).toEqual({ estado: 'reparado', fecha_reparacion: hoy })
    expect(await screen.findByText('No hay baches validados ni en reparación.')).toBeInTheDocument()
  })

  it('al reparar el único bache de una página mayor que 1 regresa a la página anterior', async () => {
    const { api, u } = await abrirSeguimiento({
      'GET /api/moderacion/seguimiento': ({ url }) =>
        url.searchParams.get('pagina') === '2' ? pagina([EN_REPARACION], 11, 2) : pagina([VALIDADO], 11, 1),
      'POST /api/reportes/11/estado': { cuerpo: { ...EN_REPARACION, estado: 'reparado' } },
    })

    await u.click(await screen.findByRole('button', { name: 'Siguiente' }))
    await u.click(await screen.findByRole('button', { name: 'Marcar reparado BCH-2026-000011' }))
    await u.click(screen.getByRole('button', { name: 'Confirmar: Reparado' }))

    expect(await screen.findByText('El reporte BCH-2026-000011 quedó como Reparado.')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'BCH-2026-000010' })).toBeInTheDocument()
    expect(api.de('GET /api/moderacion/seguimiento').map((l) => l.url.searchParams.get('pagina'))).toEqual(['1', '2', '1'])
  })

  it('marcar en reparación el único bache de la página 2 no cambia de página (el bache sigue en la lista)', async () => {
    const solo = { ...VALIDADO, id: 12, folio: 'BCH-2026-000012' }
    const { api, u } = await abrirSeguimiento({
      'GET /api/moderacion/seguimiento': ({ url }) =>
        url.searchParams.get('pagina') === '2' ? pagina([solo], 11, 2) : pagina([VALIDADO], 11, 1),
      'POST /api/reportes/12/estado': { cuerpo: { ...solo, estado: 'en_reparacion' } },
    })

    await u.click(await screen.findByRole('button', { name: 'Siguiente' }))
    await u.click(await screen.findByRole('button', { name: 'Marcar en reparación BCH-2026-000012' }))
    await u.click(screen.getByRole('button', { name: 'Confirmar: En reparación' }))

    await screen.findByText('El reporte BCH-2026-000012 quedó como En reparación.')
    expect(api.de('GET /api/moderacion/seguimiento').map((l) => l.url.searchParams.get('pagina'))).toEqual(['1', '2', '2'])
  })

  it('muestra junto a la fecha el error que manda el servidor (422)', async () => {
    const { u } = await abrirSeguimiento({
      'GET /api/moderacion/seguimiento': pagina([EN_REPARACION]),
      'POST /api/reportes/11/estado': {
        status: 422,
        cuerpo: {
          detail: 'Revisa los datos marcados',
          codigo: 'VALIDACION',
          campos: { fecha_reparacion: 'La fecha de reparación no puede ser anterior al reporte' },
        },
      },
    })

    await u.click(await screen.findByRole('button', { name: 'Marcar reparado BCH-2026-000011' }))
    await u.click(screen.getByRole('button', { name: 'Confirmar: Reparado' }))

    expect(await screen.findByText('La fecha de reparación no puede ser anterior al reporte')).toBeInTheDocument()
    expect(screen.getByLabelText(/Fecha de reparación/)).toHaveAttribute('aria-invalid', 'true')
  })

  it('un salto que ya no es válido (409) se avisa y la lista se refresca', async () => {
    const { api, u } = await abrirSeguimiento({
      'GET /api/moderacion/seguimiento': [pagina([VALIDADO]), pagina([], 0)],
      'POST /api/reportes/10/estado': {
        status: 409,
        cuerpo: { detail: 'El reporte BCH-2026-000010 está en «En reparación»', codigo: 'TRANSICION_INVALIDA' },
      },
    })

    await u.click(await screen.findByRole('button', { name: 'Marcar en reparación BCH-2026-000010' }))
    await u.click(screen.getByRole('button', { name: 'Confirmar: En reparación' }))

    expect(await screen.findByText(/está en «En reparación»/)).toBeInTheDocument()
    expect(api.de('GET /api/moderacion/seguimiento')).toHaveLength(2)
  })
})

describe('Moderación: coordinador (RN-05)', () => {
  it('solo ve la pestaña "En seguimiento" y no pide la bandeja', async () => {
    // Si la pantalla pidiera la bandeja, simularApi no tendría esa ruta y la prueba fallaría
    simularApi({ ...CATALOGOS, 'GET /api/moderacion/seguimiento': pagina([]) })
    renderizar(COORDINADOR)
    expect(await screen.findByRole('tab', { name: 'En seguimiento' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.queryByRole('tab', { name: 'Por revisar' })).not.toBeInTheDocument()
  })
})
