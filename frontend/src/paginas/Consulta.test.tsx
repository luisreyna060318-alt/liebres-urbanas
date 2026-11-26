import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import type { ReportePublico, UsuarioPublico } from '../api/tipos.ts'
import { authFalso, ConAuth, MODERADOR, simularApi } from '../pruebas/ayudas.tsx'
import type { RespuestaSimulada } from '../pruebas/ayudas.tsx'
import { COLONIAS, encharcamientoMio, reporteMio } from '../pruebas/datos.ts'
import Consulta from './Consulta.tsx'

// ReportePublico (sin los campos que solo ve el autor)
function publico(parcial: Partial<ReportePublico> = {}): ReportePublico {
  const { puede_editar: _a, motivo_rechazo: _b, ...resto } = reporteMio()
  return { ...resto, ...parcial }
}

const BACHE = publico({ id: 1, folio: 'BCH-2026-000001' })
const { puede_editar: _c, motivo_rechazo: _d, ...ENCHARCAMIENTO } = encharcamientoMio({ id: 2, folio: 'ENC-2026-000002' })

function pagina(items: ReportePublico[], total = items.length, numero = 1): RespuestaSimulada {
  return { cuerpo: { items, total, pagina: numero, tam: 20 } }
}

const COLONIAS_API: RespuestaSimulada = { cuerpo: { items: COLONIAS, total: 2, pagina: 1, tam: 500 } }

// Muestra la URL actual para comprobar que los filtros quedan en ella
function UbicacionActual() {
  const { search } = useLocation()
  return <p data-testid="url">{search}</p>
}

function renderizar(ruta = '/', usuario: UsuarioPublico | null = null) {
  return render(
    <ConAuth valor={authFalso({ usuario })}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route
            path="/"
            element={
              <>
                <Consulta />
                <UbicacionActual />
              </>
            }
          />
          <Route path="/reportes/:id" element={<p>Pantalla de detalle</p>} />
        </Routes>
      </MemoryRouter>
    </ConAuth>,
  )
}

describe('Consulta pública (HU-04.1 y HU-04.2)', () => {
  it('muestra "cargando" y luego la lista con baches y encharcamientos distinguidos por texto e ícono', async () => {
    simularApi({ 'GET /api/reportes': pagina([BACHE, ENCHARCAMIENTO]), 'GET /api/colonias': COLONIAS_API })
    renderizar()

    expect(screen.getByText('Cargando reportes…')).toBeInTheDocument()
    const bache = (await screen.findByRole('heading', { name: 'BCH-2026-000001' })).closest('article')!
    expect(within(bache).getByText(/^Bache/)).toBeInTheDocument()
    expect(within(bache).getByText('🚧')).toHaveAttribute('aria-hidden', 'true')
    const charco = screen.getByRole('heading', { name: 'ENC-2026-000002' }).closest('article')!
    expect(within(charco).getByText(/Encharcamiento/)).toBeInTheDocument()
    expect(within(charco).getByText('Estado: Activo')).toBeInTheDocument()
    expect(within(bache).getByRole('link', { name: /Ver detalle/ })).toHaveAttribute('href', '/reportes/1')
    expect(screen.getByText('Página 1 de 1 (2 resultados)')).toBeInTheDocument()
  })

  it('si falla la consulta muestra el error y deja reintentar', async () => {
    simularApi({ 'GET /api/reportes': ['sin_red', pagina([BACHE])], 'GET /api/colonias': COLONIAS_API })
    renderizar()

    expect(await screen.findByText(/No se pudo conectar con el servidor/)).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByRole('heading', { name: 'BCH-2026-000001' })).toBeInTheDocument()
  })

  it('sin resultados con filtros ofrece "Limpiar filtros" y vuelve a la consulta sin filtros', async () => {
    const api = simularApi({
      'GET /api/reportes': ({ url }) => (url.searchParams.get('q') ? pagina([], 0) : pagina([BACHE])),
      'GET /api/colonias': COLONIAS_API,
    })
    renderizar('/?q=inexistente')

    const vacio = (await screen.findByText('No hay reportes que coincidan con los filtros.')).closest('div')!
    await userEvent.setup().click(within(vacio).getByRole('button', { name: 'Limpiar filtros' }))

    expect(await screen.findByRole('heading', { name: 'BCH-2026-000001' })).toBeInTheDocument()
    expect(screen.getByTestId('url')).toHaveTextContent(/^$/)
    expect(screen.getByLabelText(/Buscar por calle o folio/)).toHaveValue('')
    expect(api.de('GET /api/reportes').map((l) => l.url.search)).toEqual(['?q=inexistente&pagina=1', '?pagina=1'])
  })

  it('sin filtros y sin reportes dice que no hay reportes activos', async () => {
    simularApi({ 'GET /api/reportes': pagina([], 0), 'GET /api/colonias': COLONIAS_API })
    renderizar()
    expect(await screen.findByText('No hay reportes activos por ahora.')).toBeInTheDocument()
  })

  it('aplica los filtros combinados, los guarda en la URL y regresa a la página 1', async () => {
    const api = simularApi({ 'GET /api/reportes': pagina([BACHE]), 'GET /api/colonias': COLONIAS_API })
    renderizar('/?pagina=3')
    const u = userEvent.setup()

    await screen.findByRole('heading', { name: 'BCH-2026-000001' })
    await screen.findByRole('option', { name: 'Partido Escobedo' })
    await u.type(screen.getByLabelText(/Buscar por calle o folio/), 'Tecnológico')
    await u.selectOptions(screen.getByLabelText('Tipo de reporte'), 'bache')
    await u.selectOptions(screen.getByLabelText('Estado'), 'reparado')
    await u.selectOptions(screen.getByLabelText('Colonia'), '12')
    await u.selectOptions(screen.getByLabelText('Severidad'), 'alta')
    await u.type(screen.getByLabelText('Desde'), '2026-11-01')
    await u.type(screen.getByLabelText('Hasta'), '2026-11-24')
    await u.click(screen.getByRole('button', { name: 'Buscar' }))

    await screen.findByText(/categoria=bache/)
    const ultima = api.de('GET /api/reportes').at(-1)!.url.searchParams
    expect(Object.fromEntries(ultima)).toEqual({
      categoria: 'bache',
      estado: 'reparado',
      colonia_id: '12',
      severidad: 'alta',
      desde: '2026-11-01',
      hasta: '2026-11-24',
      q: 'Tecnológico',
      pagina: '1',
    })
    expect(screen.getByTestId('url').textContent).not.toContain('pagina')
  })

  it('no consulta si la fecha final es anterior a la inicial', async () => {
    const api = simularApi({ 'GET /api/reportes': pagina([BACHE]), 'GET /api/colonias': COLONIAS_API })
    renderizar()
    const u = userEvent.setup()

    await screen.findByRole('heading', { name: 'BCH-2026-000001' })
    await u.type(screen.getByLabelText('Desde'), '2026-11-20')
    await u.type(screen.getByLabelText('Hasta'), '2026-11-10')
    await u.click(screen.getByRole('button', { name: 'Buscar' }))

    expect(screen.getByText('La fecha final no puede ser anterior a la inicial')).toBeInTheDocument()
    expect(api.de('GET /api/reportes')).toHaveLength(1)
  })

  it('pagina de 20 en 20 conservando los filtros de la URL', async () => {
    const api = simularApi({
      'GET /api/reportes': ({ url }) =>
        url.searchParams.get('pagina') === '2' ? pagina([ENCHARCAMIENTO], 21, 2) : pagina([BACHE], 21, 1),
      'GET /api/colonias': COLONIAS_API,
    })
    renderizar('/?categoria=bache')
    const u = userEvent.setup()

    expect(await screen.findByText('Página 1 de 2 (21 resultados)')).toBeInTheDocument()
    await u.click(screen.getByRole('button', { name: 'Siguiente' }))
    // El botón se desmonta mientras carga; el foco queda en el encabezado de resultados
    expect(screen.getByRole('heading', { name: 'Resultados' })).toHaveFocus()

    expect(await screen.findByRole('heading', { name: 'ENC-2026-000002' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Resultados' })).toHaveFocus()
    expect(screen.getByTestId('url')).toHaveTextContent('?categoria=bache&pagina=2')
    expect(api.de('GET /api/reportes').map((l) => l.url.search)).toEqual([
      '?categoria=bache&pagina=1',
      '?categoria=bache&pagina=2',
    ])
  })

  it('al buscar el formulario sigue montado: conserva el foco y pide las colonias una sola vez', async () => {
    const api = simularApi({ 'GET /api/reportes': pagina([BACHE]), 'GET /api/colonias': COLONIAS_API })
    renderizar()
    const u = userEvent.setup()

    await screen.findByRole('heading', { name: 'BCH-2026-000001' })
    const campo = screen.getByLabelText(/Buscar por calle o folio/)
    await u.type(campo, 'Tecnológico{Enter}')
    await screen.findByText(/q=Tecnol/)
    await screen.findByRole('heading', { name: 'BCH-2026-000001' })
    expect(campo).toBeInTheDocument()
    expect(campo).toHaveFocus() // Buscar con Enter no desmonta el formulario

    const buscar = screen.getByRole('button', { name: 'Buscar' })
    await u.click(buscar)
    await screen.findByRole('heading', { name: 'BCH-2026-000001' })
    expect(buscar).toHaveFocus()
    expect(screen.getByRole('form', { name: 'Filtros de reportes' })).toContainElement(document.activeElement as HTMLElement)

    expect(api.de('GET /api/colonias')).toHaveLength(1)
  })

  it('"Limpiar filtros" del formulario borra lo escrito aunque la URL ya no tenga filtros y conserva el foco', async () => {
    simularApi({ 'GET /api/reportes': pagina([BACHE]), 'GET /api/colonias': COLONIAS_API })
    renderizar()
    const u = userEvent.setup()

    await screen.findByRole('heading', { name: 'BCH-2026-000001' })
    await u.type(screen.getByLabelText(/Buscar por calle o folio/), 'sin aplicar')
    const limpiar = screen.getByRole('button', { name: 'Limpiar filtros' })
    await u.click(limpiar)

    expect(screen.getByLabelText(/Buscar por calle o folio/)).toHaveValue('')
    expect(limpiar).toHaveFocus()
  })

  it('el botón "atrás" vuelve a poner en el formulario los filtros de la URL', async () => {
    simularApi({ 'GET /api/reportes': pagina([BACHE]), 'GET /api/colonias': COLONIAS_API })
    function Atras() {
      const irAtras = useNavigate()
      return <button onClick={() => void irAtras(-1)}>Atrás</button>
    }
    render(
      <ConAuth valor={authFalso()}>
        <MemoryRouter initialEntries={['/?q=uno', '/?q=dos']} initialIndex={1}>
          <Consulta />
          <Atras />
        </MemoryRouter>
      </ConAuth>,
    )
    await screen.findByRole('heading', { name: 'BCH-2026-000001' })
    expect(screen.getByLabelText(/Buscar por calle o folio/)).toHaveValue('dos')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Atrás' }))
    await waitFor(() => expect(screen.getByLabelText(/Buscar por calle o folio/)).toHaveValue('uno'))
  })

  it('el estado Rechazado solo se ofrece a moderación', async () => {
    simularApi({ 'GET /api/reportes': pagina([BACHE]), 'GET /api/colonias': COLONIAS_API })
    const { unmount } = renderizar()
    await screen.findByRole('heading', { name: 'BCH-2026-000001' })
    expect(within(screen.getByLabelText('Estado')).queryByRole('option', { name: 'Rechazado' })).not.toBeInTheDocument()
    unmount()

    renderizar('/', MODERADOR)
    await screen.findByRole('heading', { name: 'BCH-2026-000001' })
    expect(within(screen.getByLabelText('Estado')).getByRole('option', { name: 'Rechazado' })).toBeInTheDocument()
  })
})
