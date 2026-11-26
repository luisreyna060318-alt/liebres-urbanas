import { act, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { ReporteCercano } from '../api/tipos.ts'
import { respuestaJson, simularApi, simularGeolocalizacion } from '../pruebas/ayudas.tsx'
import { GEO_SIN_COLONIA, GEO_TECNOLOGICO, reporteCercano } from '../pruebas/datos.ts'
import Zona from './Zona.tsx'

function renderizar() {
  return render(
    <MemoryRouter initialEntries={['/zona']}>
      <Zona />
    </MemoryRouter>,
  )
}

function zona(items: ReporteCercano[], total = items.length) {
  return { cuerpo: { centro: { lat: 31.7001, lon: -106.4302 }, radio_m: 1000, total, items } }
}

const BACHE = reporteCercano({ id: 10, folio: 'BCH-2026-000010', distancia_m: 120 })
const INTRANSITABLE = reporteCercano({
  id: 20,
  folio: 'ENC-2026-000020',
  categoria: 'encharcamiento',
  tipo_dano: null,
  nivel_agua: 'intransitable',
  hay_riesgo: true,
  estado: 'activo',
  sin_validar: false,
  distancia_m: 850,
})

async function buscarDireccionEscrita(texto = 'Av. Tecnológico 1340') {
  const usuario = userEvent.setup()
  await usuario.type(screen.getByLabelText('Dirección'), texto)
  await usuario.click(screen.getByRole('button', { name: 'Buscar' }))
  return usuario
}

describe('¿Cómo está mi zona? (HU-04.3)', () => {
  it('no busca mientras se escribe: solo al pulsar Buscar', async () => {
    const api = simularApi({ 'GET /api/geo/buscar': { cuerpo: { resultados: [GEO_TECNOLOGICO] } }, 'GET /api/zona': zona([BACHE]) })
    renderizar()

    const usuario = userEvent.setup()
    await usuario.type(screen.getByLabelText('Dirección'), 'Av. Tecnológico')
    expect(api.de('GET /api/geo/buscar')).toHaveLength(0)

    await usuario.click(screen.getByRole('button', { name: 'Buscar' }))
    expect(await screen.findByText('BCH-2026-000010')).toBeInTheDocument()
    expect(api.de('GET /api/geo/buscar')).toHaveLength(1)
  })

  it('muestra los reportes con su distancia y un enlace al detalle', async () => {
    const api = simularApi({ 'GET /api/geo/buscar': { cuerpo: { resultados: [GEO_TECNOLOGICO] } }, 'GET /api/zona': zona([BACHE]) })
    renderizar()
    await buscarDireccionEscrita()

    const tarjeta = (await screen.findByRole('heading', { name: 'BCH-2026-000010' })).closest('article')!
    expect(within(tarjeta).getByText(/a 120 m/)).toBeInTheDocument()
    expect(within(tarjeta).getByRole('link', { name: /Ver detalle/ })).toHaveAttribute('href', '/reportes/10')
    expect(screen.getByText(/Hay 1 reporte activo a 1 km/)).toBeInTheDocument()

    const llamada = api.de('GET /api/zona')[0]
    expect(llamada.url.searchParams.get('lat')).toBe('31.7001')
    expect(llamada.url.searchParams.get('lon')).toBe('-106.4302')
  })

  it('muestra "Cargando" mientras llegan los reportes', async () => {
    // La respuesta de la zona se queda pendiente hasta que la prueba la libera
    let liberar: (r: Response) => void = () => {}
    vi.stubGlobal(
      'fetch',
      vi.fn((entrada: RequestInfo | URL) =>
        String(entrada).includes('/api/geo/buscar')
          ? Promise.resolve(respuestaJson({ resultados: [GEO_TECNOLOGICO] }))
          : new Promise<Response>((resolver) => (liberar = resolver)),
      ),
    )
    renderizar()
    await buscarDireccionEscrita()

    expect(await screen.findByText('Buscando reportes en tu zona…')).toBeInTheDocument()
    liberar(respuestaJson(zona([BACHE]).cuerpo))
    expect(await screen.findByText('BCH-2026-000010')).toBeInTheDocument()
  })

  it('sin reportes muestra "No hay reportes activos a 1 km"', async () => {
    simularApi({ 'GET /api/geo/buscar': { cuerpo: { resultados: [GEO_TECNOLOGICO] } }, 'GET /api/zona': zona([]) })
    renderizar()
    await buscarDireccionEscrita()

    expect(await screen.findByText('No hay reportes activos a 1 km.')).toBeInTheDocument()
  })

  it('si falla la consulta de la zona, muestra el error y permite reintentar', async () => {
    const api = simularApi({
      'GET /api/geo/buscar': { cuerpo: { resultados: [GEO_TECNOLOGICO] } },
      'GET /api/zona': [{ status: 500, cuerpo: { detail: 'Error inesperado', codigo: 'ERROR_INTERNO' } }, zona([BACHE])],
    })
    renderizar()
    const usuario = await buscarDireccionEscrita()

    expect(await screen.findByRole('alert')).toHaveTextContent('Error inesperado')
    await usuario.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByText('BCH-2026-000010')).toBeInTheDocument()
    expect(api.de('GET /api/zona')).toHaveLength(2)
  })

  it('con varias direcciones deja elegir y consulta la elegida', async () => {
    const api = simularApi({
      'GET /api/geo/buscar': { cuerpo: { resultados: [GEO_TECNOLOGICO, GEO_SIN_COLONIA] } },
      'GET /api/zona': zona([BACHE]),
    })
    renderizar()
    const usuario = await buscarDireccionEscrita('Tecnológico')

    expect(api.de('GET /api/zona')).toHaveLength(0) // todavía no se eligió
    await usuario.click(screen.getByRole('button', { name: /Calle Sin Colonia 5/ }))

    expect(await screen.findByText('BCH-2026-000010')).toBeInTheDocument()
    expect(api.de('GET /api/zona')[0].url.searchParams.get('lat')).toBe('31.71')
  })

  it('dirección no encontrada: mensaje y reintento que lleva de vuelta al campo', async () => {
    const api = simularApi({
      'GET /api/geo/buscar': [{ cuerpo: { resultados: [] } }, { cuerpo: { resultados: [GEO_TECNOLOGICO] } }],
      'GET /api/zona': zona([BACHE]),
    })
    renderizar()
    const usuario = await buscarDireccionEscrita('Calle que no existe')

    expect(await screen.findByText(/No encontramos esa dirección/)).toBeInTheDocument()
    await usuario.click(screen.getByRole('button', { name: 'Intentar de nuevo' }))
    expect(screen.queryByText(/No encontramos esa dirección/)).not.toBeInTheDocument()
    expect(screen.getByLabelText('Dirección')).toHaveFocus()

    await usuario.clear(screen.getByLabelText('Dirección'))
    await usuario.type(screen.getByLabelText('Dirección'), 'Av. Tecnológico 1340')
    await usuario.click(screen.getByRole('button', { name: 'Buscar' }))
    expect(await screen.findByText('BCH-2026-000010')).toBeInTheDocument()
    expect(api.de('GET /api/geo/buscar')).toHaveLength(2)
  })

  it('si el servicio de direcciones no responde (503) lo explica y deja reintentar', async () => {
    simularApi({
      'GET /api/geo/buscar': [
        { status: 503, cuerpo: { detail: 'Servicio caído', codigo: 'SERVICIO_NO_DISPONIBLE' } },
        { cuerpo: { resultados: [GEO_TECNOLOGICO] } },
      ],
      'GET /api/zona': zona([BACHE]),
    })
    renderizar()
    const usuario = await buscarDireccionEscrita()

    expect(await screen.findByText(/servicio de búsqueda de direcciones no está disponible/)).toBeInTheDocument()
    await usuario.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByText('BCH-2026-000010')).toBeInTheDocument()
  })

  it('resalta el encharcamiento intransitable con texto y lo muestra primero', async () => {
    // El servidor ya lo manda al inicio aunque esté más lejos; la pantalla respeta ese orden
    simularApi({
      'GET /api/geo/buscar': { cuerpo: { resultados: [GEO_TECNOLOGICO] } },
      'GET /api/zona': zona([INTRANSITABLE, BACHE]),
    })
    renderizar()
    await buscarDireccionEscrita()

    await screen.findByText('BCH-2026-000010')
    const folios = screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)
    expect(folios).toEqual(['ENC-2026-000020', 'BCH-2026-000010'])

    const tarjeta = screen.getByRole('heading', { name: 'ENC-2026-000020' }).closest('article')!
    expect(within(tarjeta).getByText(/Intransitable: evita pasar por aquí/)).toBeInTheDocument()
    expect(within(tarjeta).getByText(/a 850 m/)).toBeInTheDocument()
    // El bache no lleva la leyenda
    const bache = screen.getByRole('heading', { name: 'BCH-2026-000010' }).closest('article')!
    expect(within(bache).queryByText(/evita pasar por aquí/)).not.toBeInTheDocument()
  })

  it('si la ubicación del dispositivo cae fuera de Juárez (422) explica el motivo y no ofrece reintentar', async () => {
    simularApi({
      'GET /api/zona': {
        status: 422,
        cuerpo: { detail: 'El punto está fuera de Ciudad Juárez', codigo: 'FUERA_DEL_MUNICIPIO' },
      },
    })
    simularGeolocalizacion({ lat: 32.5, lon: -117.0 })
    renderizar()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Usar mi ubicación' }))

    expect(
      await screen.findByText('Ese punto está fuera de Ciudad Juárez; escribe una dirección de la ciudad.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reintentar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Dirección')).toBeEnabled()
  })

  it('ignora la respuesta de una búsqueda anterior si ya se lanzó otra', async () => {
    // Cada búsqueda de dirección queda pendiente hasta que la prueba la libera, en el orden que quiera
    const pendientes: ((r: Response) => void)[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn((entrada: RequestInfo | URL) => {
        const url = String(entrada)
        if (url.includes('/api/geo/buscar')) return new Promise<Response>((resolver) => pendientes.push(resolver))
        return Promise.resolve(respuestaJson(zona([BACHE]).cuerpo))
      }),
    )
    renderizar()
    const campo = screen.getByLabelText('Dirección')
    const formulario = screen.getByRole('search', { name: 'Buscar una zona' })

    fireEvent.change(campo, { target: { value: 'Primera dirección' } })
    fireEvent.submit(formulario)
    fireEvent.change(campo, { target: { value: 'Segunda dirección' } })
    fireEvent.submit(formulario)
    expect(pendientes).toHaveLength(2)

    // Primero llega la segunda y después la primera (más lenta)
    pendientes[1](respuestaJson({ resultados: [GEO_TECNOLOGICO] }))
    expect(await screen.findByText(/cerca de: Av. Tecnológico 1340/)).toBeInTheDocument()
    pendientes[0](respuestaJson({ resultados: [GEO_SIN_COLONIA] }))
    await act(async () => {
      await Promise.resolve()
    })

    expect(screen.getByText(/cerca de: Av. Tecnológico 1340/)).toBeInTheDocument()
    expect(screen.queryByText(/Calle Sin Colonia/)).not.toBeInTheDocument()
  })

  it('"Usar mi ubicación" consulta con las coordenadas del dispositivo', async () => {
    const api = simularApi({ 'GET /api/zona': zona([BACHE]) })
    simularGeolocalizacion({ lat: 31.69, lon: -106.42 })
    renderizar()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Usar mi ubicación' }))

    expect(await screen.findByText('BCH-2026-000010')).toBeInTheDocument()
    expect(screen.getByText(/cerca de: Tu ubicación/)).toBeInTheDocument()
    expect(api.de('GET /api/zona')[0].url.searchParams.get('lat')).toBe('31.69')
  })

  it('si se niega el permiso de ubicación, explica y deja buscar a mano', async () => {
    simularApi({})
    simularGeolocalizacion({ codigo: 1 })
    renderizar()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Usar mi ubicación' }))

    expect(await screen.findByText(/No diste permiso para usar tu ubicación/)).toBeInTheDocument()
    expect(screen.getByLabelText('Dirección')).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Buscar' })).toBeEnabled()
  })
})
