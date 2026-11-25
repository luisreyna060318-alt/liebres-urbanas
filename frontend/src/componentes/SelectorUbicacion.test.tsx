import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import { COLONIAS, GEO_SIN_COLONIA, GEO_TECNOLOGICO } from '../pruebas/datos.ts'
import { simularApi, simularGeolocalizacion } from '../pruebas/ayudas.tsx'
import { UBICACION_VACIA } from '../utils/reportes.ts'
import type { DatosUbicacion } from '../utils/reportes.ts'
import SelectorUbicacion from './SelectorUbicacion.tsx'

const COLONIAS_OK = { cuerpo: { items: COLONIAS, total: 2, pagina: 1, tam: 500 } }

// Guarda el valor igual que lo hace el formulario que contiene al selector (y lo escribe en pantalla para verificarlo)
function Prueba() {
  const [valor, setValor] = useState<DatosUbicacion>(UBICACION_VACIA)
  return (
    <form onSubmit={(e) => e.preventDefault()}>
      <SelectorUbicacion valor={valor} onCambio={setValor} />
    </form>
  )
}

describe('SelectorUbicacion', () => {
  it('no busca mientras se escribe: solo al pulsar Buscar, y muestra hasta 5 resultados', async () => {
    const seis = Array.from({ length: 6 }, (_, i) => ({ ...GEO_TECNOLOGICO, etiqueta: `Resultado ${i + 1}`, lat: 31.7 + i / 1000 }))
    const api = simularApi({ 'GET /api/colonias': COLONIAS_OK, 'GET /api/geo/buscar': { cuerpo: { resultados: seis } } })
    render(<Prueba />)
    const u = userEvent.setup()

    await u.type(screen.getByLabelText('Dirección'), 'Av. Tecnológico 1340')
    expect(api.de('GET /api/geo/buscar')).toHaveLength(0)

    await u.click(screen.getByRole('button', { name: 'Buscar' }))
    expect(await screen.findByText('Elige la dirección correcta:')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /^Elegir: / })).toHaveLength(5)
    expect(api.de('GET /api/geo/buscar')[0].url.searchParams.get('q')).toBe('Av. Tecnológico 1340')
  })

  it('al elegir un resultado llena calle, colonia y coordenadas, y se pueden corregir', async () => {
    simularApi({ 'GET /api/colonias': COLONIAS_OK, 'GET /api/geo/buscar': { cuerpo: { resultados: [GEO_TECNOLOGICO] } } })
    render(<Prueba />)
    const u = userEvent.setup()

    await u.type(screen.getByLabelText('Dirección'), 'Tecnológico')
    await u.click(screen.getByRole('button', { name: 'Buscar' }))
    await u.click(await screen.findByRole('button', { name: /Elegir: Av\. Tecnológico 1340/ }))

    expect(screen.getByLabelText(/Calle/)).toHaveValue('Av. Tecnológico')
    expect(await screen.findByRole('option', { name: 'Partido Escobedo (Norte)' })).toBeInTheDocument()
    expect(screen.getByLabelText(/Colonia/)).toHaveValue('12')
    expect(screen.getByLabelText(/Latitud/)).toHaveValue('31.7001')
    expect(screen.getByLabelText(/Longitud/)).toHaveValue('-106.4302')

    // La persona puede corregir la calle
    await u.clear(screen.getByLabelText(/Calle/))
    await u.type(screen.getByLabelText(/Calle/), 'Av. Tecnológico Norte')
    expect(screen.getByLabelText(/Calle/)).toHaveValue('Av. Tecnológico Norte')
  })

  it('Enter en el campo de dirección busca y no envía el formulario', async () => {
    const api = simularApi({ 'GET /api/colonias': COLONIAS_OK, 'GET /api/geo/buscar': { cuerpo: { resultados: [GEO_TECNOLOGICO] } } })
    render(<Prueba />)
    await userEvent.setup().type(screen.getByLabelText('Dirección'), 'Tecnológico{Enter}')

    expect(await screen.findByRole('button', { name: /Elegir:/ })).toBeInTheDocument()
    expect(api.de('GET /api/geo/buscar')).toHaveLength(1)
  })

  it('si la colonia no coincide con el catálogo pide elegirla de la lista', async () => {
    simularApi({ 'GET /api/colonias': COLONIAS_OK, 'GET /api/geo/buscar': { cuerpo: { resultados: [GEO_SIN_COLONIA] } } })
    render(<Prueba />)
    const u = userEvent.setup()

    await u.type(screen.getByLabelText('Dirección'), 'Calle Sin Colonia')
    await u.click(screen.getByRole('button', { name: 'Buscar' }))
    await u.click(await screen.findByRole('button', { name: /Elegir:/ }))

    expect(screen.getByText(/No reconocimos la colonia/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Colonia/)).toHaveValue('')
    expect(screen.getByLabelText(/Calle/)).toHaveValue('Calle Sin Colonia')
  })

  it('sin resultados muestra un mensaje y deja intentar de nuevo', async () => {
    simularApi({ 'GET /api/colonias': COLONIAS_OK, 'GET /api/geo/buscar': [{ cuerpo: { resultados: [] } }, { cuerpo: { resultados: [GEO_TECNOLOGICO] } }] })
    render(<Prueba />)
    const u = userEvent.setup()

    await u.type(screen.getByLabelText('Dirección'), 'Calle inventada')
    await u.click(screen.getByRole('button', { name: 'Buscar' }))
    expect(await screen.findByText(/No encontramos esa dirección/)).toBeInTheDocument()

    await u.clear(screen.getByLabelText('Dirección'))
    await u.type(screen.getByLabelText('Dirección'), 'Tecnológico')
    await u.click(screen.getByRole('button', { name: 'Buscar' }))
    expect(await screen.findByRole('button', { name: /Elegir:/ })).toBeInTheDocument()
    expect(screen.queryByText(/No encontramos esa dirección/)).not.toBeInTheDocument()
  })

  it('con 503 SERVICIO_NO_DISPONIBLE avisa y deja capturar calle, colonia y coordenadas a mano', async () => {
    simularApi({
      'GET /api/colonias': COLONIAS_OK,
      'GET /api/geo/buscar': { status: 503, cuerpo: { detail: 'Nominatim no responde', codigo: 'SERVICIO_NO_DISPONIBLE' } },
    })
    render(<Prueba />)
    const u = userEvent.setup()

    await u.type(screen.getByLabelText('Dirección'), 'Tecnológico')
    await u.click(screen.getByRole('button', { name: 'Buscar' }))
    expect(await screen.findByText(/servicio de búsqueda de direcciones no está disponible/)).toBeInTheDocument()

    await u.type(screen.getByLabelText(/Calle/), 'Calle Sexta')
    await u.selectOptions(screen.getByLabelText(/Colonia/), '13')
    await u.type(screen.getByLabelText(/Latitud/), '31.74')
    await u.type(screen.getByLabelText(/Longitud/), '-106.48')
    expect(screen.getByLabelText(/Calle/)).toHaveValue('Calle Sexta')
    expect(screen.getByLabelText(/Colonia/)).toHaveValue('13')
    expect(screen.getByLabelText(/Longitud/)).toHaveValue('-106.48')
  })

  it('"Usar mi ubicación" pide la dirección de las coordenadas del dispositivo', async () => {
    const api = simularApi({ 'GET /api/colonias': COLONIAS_OK, 'GET /api/geo/inversa': { cuerpo: GEO_TECNOLOGICO } })
    simularGeolocalizacion({ lat: 31.7001, lon: -106.4302 })
    render(<Prueba />)

    await userEvent.setup().click(screen.getByRole('button', { name: 'Usar mi ubicación' }))

    expect(await screen.findByDisplayValue('Av. Tecnológico')).toBeInTheDocument()
    expect(api.de('GET /api/geo/inversa')[0].url.search).toBe('?lat=31.7001&lon=-106.4302')
    expect(screen.getByLabelText(/Latitud/)).toHaveValue('31.7001')
  })

  it('si el permiso de ubicación se niega, lo explica y ofrece capturar a mano', async () => {
    simularApi({ 'GET /api/colonias': COLONIAS_OK })
    simularGeolocalizacion({ codigo: 1 })
    render(<Prueba />)

    await userEvent.setup().click(screen.getByRole('button', { name: 'Usar mi ubicación' }))

    expect(await screen.findByText(/No diste permiso para usar tu ubicación/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Latitud/)).toBeInTheDocument() // ya se puede capturar a mano
  })

  it('si el navegador no tiene geolocalización lo avisa', async () => {
    simularApi({ 'GET /api/colonias': COLONIAS_OK })
    render(<Prueba />) // jsdom no trae navigator.geolocation

    await userEvent.setup().click(screen.getByRole('button', { name: 'Usar mi ubicación' }))

    expect(await screen.findByText(/Tu navegador no permite obtener la ubicación/)).toBeInTheDocument()
  })

  it('si la dirección de la ubicación no se puede obtener (503) conserva las coordenadas del dispositivo', async () => {
    simularApi({
      'GET /api/colonias': COLONIAS_OK,
      'GET /api/geo/inversa': { status: 503, cuerpo: { detail: 'Sin servicio', codigo: 'SERVICIO_NO_DISPONIBLE' } },
    })
    simularGeolocalizacion({ lat: 31.7123456789, lon: -106.4 })
    render(<Prueba />)

    await userEvent.setup().click(screen.getByRole('button', { name: 'Usar mi ubicación' }))

    expect(await screen.findByText(/no está disponible/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Latitud/)).toHaveValue('31.712346')
    expect(screen.getByLabelText(/Longitud/)).toHaveValue('-106.4')
  })
})
