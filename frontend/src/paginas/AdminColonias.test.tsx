import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import type { Colonia } from '../api/tipos.ts'
import { authFalso, COORDINADOR, ConAuth, simularApi } from '../pruebas/ayudas.tsx'
import type { RespuestaSimulada } from '../pruebas/ayudas.tsx'
import AdminColonias from './AdminColonias.tsx'

const CENTRO = { id: 1, nombre: 'Centro' }
const NORTE = { id: 2, nombre: 'Norte' }

function colonia(id: number, nombre: string, extra: Partial<Colonia> = {}): Colonia {
  return { id, nombre, sector: CENTRO, activa: true, lat: 31.7, lon: -106.4, ...extra }
}

const ACTIVA = colonia(10, 'Colonia Ficticia Uno')
const INACTIVA = colonia(11, 'Colonia Ficticia Cerrada', { activa: false, sector: NORTE })

function pagina(items: Colonia[], total = items.length, numero = 1): RespuestaSimulada {
  return { cuerpo: { items, total, pagina: numero, tam: 10 } }
}

const SECTORES: Record<string, RespuestaSimulada> = { 'GET /api/sectores': { cuerpo: [CENTRO, NORTE] } }

function renderizar() {
  return render(
    <ConAuth valor={authFalso({ usuario: COORDINADOR })}>
      <MemoryRouter>
        <AdminColonias />
      </MemoryRouter>
    </ConAuth>,
  )
}

describe('Administrar colonias (HU-06.1)', () => {
  it('lista activas e inactivas con su sector y pide todas con solo_activas=false', async () => {
    const api = simularApi({ ...SECTORES, 'GET /api/colonias': pagina([ACTIVA, INACTIVA]) })
    renderizar()

    const fila = (await screen.findByRole('row', { name: /Colonia Ficticia Uno/ })) as HTMLElement
    expect(within(fila).getByText('Centro')).toBeInTheDocument()
    expect(within(fila).getByText('Activa')).toBeInTheDocument()
    expect(within(screen.getByRole('row', { name: /Colonia Ficticia Cerrada/ })).getByText('Inactiva')).toBeInTheDocument()
    // Encabezados con scope para lectores de pantalla
    expect(screen.getByRole('columnheader', { name: 'Sector' })).toHaveAttribute('scope', 'col')
    expect(api.de('GET /api/colonias')[0].url.searchParams.get('solo_activas')).toBe('false')
    expect(api.de('GET /api/colonias')[0].url.searchParams.get('tam')).toBe('10')
  })

  it('sin colonias muestra el mensaje de vacío y si falla deja reintentar', async () => {
    simularApi({ ...SECTORES, 'GET /api/colonias': ['sin_red', pagina([])] })
    renderizar()

    expect(await screen.findByText(/No se pudo conectar con el servidor/)).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByText('Aún no hay colonias. Crea la primera.')).toBeInTheDocument()
  })

  it('busca por nombre y filtra por sector reiniciando la página', async () => {
    const api = simularApi({ ...SECTORES, 'GET /api/colonias': pagina([ACTIVA]) })
    renderizar()
    const u = userEvent.setup()

    await screen.findByRole('row', { name: /Colonia Ficticia Uno/ })
    await u.type(screen.getByLabelText('Buscar por nombre'), 'ficticia')
    await u.click(screen.getByRole('button', { name: 'Buscar' }))
    await u.selectOptions(screen.getByLabelText('Sector'), '2')

    const ultima = api.de('GET /api/colonias').at(-1)!.url.searchParams
    expect(ultima.get('q')).toBe('ficticia')
    expect(ultima.get('sector_id')).toBe('2')
    expect(ultima.get('pagina')).toBe('1')
  })

  it('pagina de 10 en 10', async () => {
    const api = simularApi({
      ...SECTORES,
      'GET /api/colonias': ({ url }) => (url.searchParams.get('pagina') === '2' ? pagina([INACTIVA], 11, 2) : pagina([ACTIVA], 11, 1)),
    })
    renderizar()

    expect(await screen.findByText('Página 1 de 2 (11 resultados)')).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(await screen.findByRole('row', { name: /Colonia Ficticia Cerrada/ })).toBeInTheDocument()
    expect(api.de('GET /api/colonias').map((l) => l.url.searchParams.get('pagina'))).toEqual(['1', '2'])
  })

  it('crea una colonia con POST y refresca la lista', async () => {
    const api = simularApi({
      ...SECTORES,
      'GET /api/colonias': [pagina([ACTIVA]), pagina([ACTIVA, colonia(12, 'Colonia Nueva')])],
      'POST /api/colonias': { status: 201, cuerpo: colonia(12, 'Colonia Nueva') },
    })
    renderizar()
    const u = userEvent.setup()

    await screen.findByRole('row', { name: /Colonia Ficticia Uno/ })
    await u.click(screen.getByRole('button', { name: 'Nueva colonia' }))
    await u.type(screen.getByLabelText('Nombre *'), 'Colonia Nueva')
    await u.selectOptions(screen.getByLabelText(/^Sector/, { selector: '#colonia-sector' }), '1')
    await u.type(screen.getByLabelText('Latitud'), '31.73')
    await u.type(screen.getByLabelText('Longitud'), '-106.48')
    await u.click(screen.getByRole('button', { name: 'Crear colonia' }))

    expect(await screen.findByText('Se creó la colonia Colonia Nueva.')).toBeInTheDocument()
    expect(api.de('POST /api/colonias')[0].cuerpo).toEqual({ nombre: 'Colonia Nueva', sector_id: 1, lat: 31.73, lon: -106.48 })
    expect(await screen.findByRole('row', { name: /Colonia Nueva/ })).toBeInTheDocument()
  })

  it('valida en el cliente: nombre vacío, sector sin elegir y una sola coordenada', async () => {
    const api = simularApi({ ...SECTORES, 'GET /api/colonias': pagina([ACTIVA]) })
    renderizar()
    const u = userEvent.setup()

    await screen.findByRole('row', { name: /Colonia Ficticia Uno/ })
    await u.click(screen.getByRole('button', { name: 'Nueva colonia' }))
    await u.type(screen.getByLabelText('Latitud'), '31.7')
    await u.click(screen.getByRole('button', { name: 'Crear colonia' }))

    expect(screen.getByText(/El nombre debe tener al menos 2 caracteres/)).toBeInTheDocument()
    expect(screen.getByText('Elige un sector.')).toBeInTheDocument()
    expect(screen.getByText(/Captura latitud y longitud juntas/)).toBeInTheDocument()
    expect(api.de('POST /api/colonias')).toHaveLength(0)
  })

  it('muestra los errores por campo del servidor y conserva lo capturado', async () => {
    simularApi({
      ...SECTORES,
      'GET /api/colonias': pagina([ACTIVA]),
      'POST /api/colonias': {
        status: 422,
        cuerpo: { detail: 'Revisa los datos marcados', codigo: 'VALIDACION', campos: { lat: 'Las coordenadas deben estar dentro de Ciudad Juárez' } },
      },
    })
    renderizar()
    const u = userEvent.setup()

    await screen.findByRole('row', { name: /Colonia Ficticia Uno/ })
    await u.click(screen.getByRole('button', { name: 'Nueva colonia' }))
    await u.type(screen.getByLabelText('Nombre *'), 'Colonia Lejana')
    await u.selectOptions(screen.getByLabelText(/^Sector/, { selector: '#colonia-sector' }), '1')
    await u.type(screen.getByLabelText('Latitud'), '19.4')
    await u.type(screen.getByLabelText('Longitud'), '-99.1')
    await u.click(screen.getByRole('button', { name: 'Crear colonia' }))

    expect(await screen.findByText(/Las coordenadas deben estar dentro de Ciudad Juárez/)).toBeInTheDocument()
    expect(screen.getByLabelText('Latitud')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('Nombre *')).toHaveValue('Colonia Lejana')
  })

  it('muestra el 409 del nombre repetido en el mismo sector', async () => {
    simularApi({
      ...SECTORES,
      'GET /api/colonias': pagina([ACTIVA]),
      'POST /api/colonias': {
        status: 409,
        cuerpo: { detail: 'Ese sector ya tiene una colonia con ese nombre. Elige otro nombre', codigo: 'COLONIA_DUPLICADA' },
      },
    })
    renderizar()
    const u = userEvent.setup()

    await screen.findByRole('row', { name: /Colonia Ficticia Uno/ })
    await u.click(screen.getByRole('button', { name: 'Nueva colonia' }))
    await u.type(screen.getByLabelText('Nombre *'), 'Colonia Ficticia Uno')
    await u.selectOptions(screen.getByLabelText(/^Sector/, { selector: '#colonia-sector' }), '1')
    await u.click(screen.getByRole('button', { name: 'Crear colonia' }))

    expect(await screen.findByText(/Ese sector ya tiene una colonia con ese nombre/)).toBeInTheDocument()
  })

  it('edita una colonia precargada con PUT que incluye activa', async () => {
    const api = simularApi({
      ...SECTORES,
      'GET /api/colonias': pagina([ACTIVA]),
      'PUT /api/colonias/10': { cuerpo: colonia(10, 'Colonia Renombrada') },
    })
    renderizar()
    const u = userEvent.setup()

    await u.click(await screen.findByRole('button', { name: /Editar Colonia Ficticia Uno/ }))
    expect(screen.getByLabelText('Nombre *')).toHaveValue('Colonia Ficticia Uno')
    expect(screen.getByLabelText('Latitud')).toHaveValue('31.7')
    await u.clear(screen.getByLabelText('Nombre *'))
    await u.type(screen.getByLabelText('Nombre *'), 'Colonia Renombrada')
    await u.click(screen.getByRole('checkbox', { name: /Activa/ }))
    await u.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    expect(await screen.findByText('Se guardaron los cambios de Colonia Renombrada.')).toBeInTheDocument()
    expect(api.de('PUT /api/colonias/10')[0].cuerpo).toEqual({
      nombre: 'Colonia Renombrada', sector_id: 1, lat: 31.7, lon: -106.4, activa: false,
    })
  })

  it('desactiva y activa con un botón', async () => {
    const api = simularApi({
      ...SECTORES,
      'GET /api/colonias': [pagina([ACTIVA, INACTIVA]), pagina([{ ...ACTIVA, activa: false }, INACTIVA])],
      'PUT /api/colonias/10': { cuerpo: { ...ACTIVA, activa: false } },
    })
    renderizar()
    const u = userEvent.setup()

    await u.click(await screen.findByRole('button', { name: /Desactivar Colonia Ficticia Uno/ }))

    expect(await screen.findByText('Colonia Ficticia Uno quedó inactiva.')).toBeInTheDocument()
    expect(api.de('PUT /api/colonias/10')[0].cuerpo).toMatchObject({ activa: false })
    expect(screen.getByRole('button', { name: /^Activar Colonia Ficticia Uno/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Activar Colonia Ficticia Cerrada/ })).toBeInTheDocument()
  })

  it('eliminar pide confirmación: cancelar no borra y confirmar llama a DELETE', async () => {
    const api = simularApi({
      ...SECTORES,
      'GET /api/colonias': [pagina([ACTIVA, INACTIVA]), pagina([INACTIVA])],
      'DELETE /api/colonias/10': { status: 204 },
    })
    renderizar()
    const u = userEvent.setup()

    await u.click(await screen.findByRole('button', { name: /Eliminar Colonia Ficticia Uno/ }))
    expect(screen.getByText(/¿Eliminar la colonia Colonia Ficticia Uno\?/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toHaveFocus()
    await u.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(api.de('DELETE /api/colonias/10')).toHaveLength(0)

    await u.click(screen.getByRole('button', { name: /Eliminar Colonia Ficticia Uno/ }))
    await u.click(screen.getByRole('button', { name: 'Sí, eliminar' }))

    expect(await screen.findByText('Se eliminó la colonia Colonia Ficticia Uno.')).toBeInTheDocument()
    expect(api.de('DELETE /api/colonias/10')).toHaveLength(1)
    expect(screen.queryByRole('row', { name: /Colonia Ficticia Uno/ })).not.toBeInTheDocument()
  })

  it('si la colonia tiene reportes (409) muestra el mensaje del servidor y la deja en la lista', async () => {
    simularApi({
      ...SECTORES,
      'GET /api/colonias': pagina([ACTIVA]),
      'DELETE /api/colonias/10': {
        status: 409,
        cuerpo: {
          detail: 'Esta colonia tiene 3 reportes y no se puede eliminar. Desactívala para que deje de ofrecerse',
          codigo: 'COLONIA_CON_REPORTES',
        },
      },
    })
    renderizar()
    const u = userEvent.setup()

    await u.click(await screen.findByRole('button', { name: /Eliminar Colonia Ficticia Uno/ }))
    await u.click(screen.getByRole('button', { name: 'Sí, eliminar' }))

    expect(await screen.findByText(/tiene 3 reportes y no se puede eliminar/)).toBeInTheDocument()
    expect(screen.getByRole('row', { name: /Colonia Ficticia Uno/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Desactivar Colonia Ficticia Uno/ })).toBeInTheDocument()
  })

  it('crea un sector y renombra otro', async () => {
    const api = simularApi({
      'GET /api/sectores': [{ cuerpo: [CENTRO, NORTE] }, { cuerpo: [CENTRO, NORTE, { id: 3, nombre: 'Sur' }] }],
      'GET /api/colonias': pagina([ACTIVA]),
      'POST /api/sectores': { status: 201, cuerpo: { id: 3, nombre: 'Sur' } },
      'PUT /api/sectores/2': { cuerpo: { id: 2, nombre: 'Norponiente' } },
    })
    renderizar()
    const u = userEvent.setup()

    await screen.findByRole('row', { name: /Colonia Ficticia Uno/ })
    await u.type(screen.getByLabelText(/^Nombre del sector nuevo/), 'Sur')
    await u.click(screen.getByRole('button', { name: 'Crear sector' }))
    expect(await screen.findByText('Se creó el sector Sur.')).toBeInTheDocument()
    expect(api.de('POST /api/sectores')[0].cuerpo).toEqual({ nombre: 'Sur' })

    await u.click(screen.getByRole('button', { name: /Renombrar Norte/ }))
    const campo = screen.getByLabelText(/^Nuevo nombre del sector Norte/)
    expect(campo).toHaveValue('Norte')
    await u.clear(campo)
    await u.type(campo, 'Norponiente')
    await u.click(screen.getByRole('button', { name: 'Guardar nombre' }))
    expect(await screen.findByText('Se renombró el sector a Norponiente.')).toBeInTheDocument()
    expect(api.de('PUT /api/sectores/2')[0].cuerpo).toEqual({ nombre: 'Norponiente' })
  })

  it('un nombre de sector repetido (409) se muestra junto al campo', async () => {
    simularApi({
      ...SECTORES,
      'GET /api/colonias': pagina([ACTIVA]),
      'POST /api/sectores': {
        status: 409,
        cuerpo: { detail: 'Ya existe un sector con ese nombre. Elige otro nombre', codigo: 'SECTOR_DUPLICADO' },
      },
    })
    renderizar()
    const u = userEvent.setup()

    await screen.findByRole('row', { name: /Colonia Ficticia Uno/ })
    await u.type(screen.getByLabelText(/^Nombre del sector nuevo/), 'Centro')
    await u.click(screen.getByRole('button', { name: 'Crear sector' }))

    expect(await screen.findByText(/Ya existe un sector con ese nombre/)).toBeInTheDocument()
  })
})
