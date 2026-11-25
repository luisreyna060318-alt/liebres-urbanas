import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { authFalso, CIUDADANO, ConAuth, simularApi } from '../pruebas/ayudas.tsx'
import type { RespuestaSimulada } from '../pruebas/ayudas.tsx'
import { COLONIAS, reporteMio, TIPOS_DANO } from '../pruebas/datos.ts'
import EditarReporte from './EditarReporte.tsx'
import MisReportes from './MisReportes.tsx'

function pagina(items: ReturnType<typeof reporteMio>[], total = items.length, numero = 1): RespuestaSimulada {
  return { cuerpo: { items, total, pagina: numero, tam: 10 } }
}

function renderizar(ruta = '/mis-reportes') {
  return render(
    <ConAuth valor={authFalso({ usuario: CIUDADANO })}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/mis-reportes" element={<MisReportes />} />
          <Route path="/mis-reportes/:id/editar" element={<EditarReporte />} />
          <Route path="/reportar" element={<p>Pantalla de reportar</p>} />
        </Routes>
      </MemoryRouter>
    </ConAuth>,
  )
}

const EDITABLE = reporteMio({ id: 1, folio: 'BCH-2026-000001', puede_editar: true })
const VALIDADO = reporteMio({ id: 2, folio: 'BCH-2026-000002', estado: 'validado', sin_validar: false, puede_editar: false })
const RECHAZADO = reporteMio({
  id: 3,
  folio: 'BCH-2026-000003',
  estado: 'rechazado',
  sin_validar: false,
  puede_editar: false,
  motivo_rechazo: { nombre: 'Duplicado', texto: 'Ya existe el reporte BCH-2026-000001.' },
})

describe('Mis reportes (HU-02.5)', () => {
  it('lista cada reporte con folio, tipo, colonia, fecha y estado', async () => {
    simularApi({ 'GET /api/mis-reportes': pagina([EDITABLE, VALIDADO]) })
    renderizar()

    const tarjeta = (await screen.findByRole('heading', { name: 'BCH-2026-000001' })).closest('article')!
    expect(within(tarjeta).getByText('Estado: Recibido')).toBeInTheDocument()
    expect(within(tarjeta).getByText(/Bache/)).toBeInTheDocument()
    expect(within(tarjeta).getByText(/Av\. Tecnológico, Partido Escobedo/)).toBeInTheDocument()
    // 21:05 UTC es 14:05 en Ciudad Juárez
    expect(within(tarjeta).getByText(/24 nov 2026, 14:05/)).toBeInTheDocument()
    expect(screen.getByText('Estado: Validado')).toBeInTheDocument()
  })

  it('sin reportes muestra un mensaje que invita a crear el primero', async () => {
    simularApi({ 'GET /api/mis-reportes': pagina([], 0) })
    renderizar()

    expect(await screen.findByText(/Aún no tienes reportes/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Crear mi primer reporte' })).toHaveAttribute('href', '/reportar')
  })

  it('si falla la consulta muestra el error y deja reintentar', async () => {
    simularApi({ 'GET /api/mis-reportes': ['sin_red', pagina([EDITABLE])] })
    renderizar()

    expect(await screen.findByText(/No se pudo conectar con el servidor/)).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByRole('heading', { name: 'BCH-2026-000001' })).toBeInTheDocument()
  })

  it('pagina de 10 en 10: "Siguiente" pide la página 2', async () => {
    const api = simularApi({
      'GET /api/mis-reportes': ({ url }) =>
        url.searchParams.get('pagina') === '2' ? pagina([VALIDADO], 11, 2) : pagina([EDITABLE], 11, 1),
    })
    renderizar()
    const u = userEvent.setup()

    expect(await screen.findByText('Página 1 de 2 (11 resultados)')).toBeInTheDocument()
    await u.click(screen.getByRole('button', { name: 'Siguiente' }))

    expect(await screen.findByRole('heading', { name: 'BCH-2026-000002' })).toBeInTheDocument()
    expect(screen.getByText('Página 2 de 2 (11 resultados)')).toBeInTheDocument()
    expect(api.de('GET /api/mis-reportes').map((l) => l.url.search)).toEqual(['?pagina=1', '?pagina=2'])
  })

  it('un reporte rechazado muestra el motivo y no ofrece Editar ni Eliminar', async () => {
    simularApi({ 'GET /api/mis-reportes': pagina([RECHAZADO]) })
    renderizar()

    expect(await screen.findByText('Estado: Rechazado')).toBeInTheDocument()
    expect(screen.getByText(/Motivo del rechazo:/).closest('p')).toHaveTextContent('Duplicado. Ya existe el reporte BCH-2026-000001.')
    expect(screen.queryByRole('link', { name: /Editar/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Eliminar/ })).not.toBeInTheDocument()
  })

  it('Editar y Eliminar aparecen solo en los reportes con puede_editar', async () => {
    simularApi({ 'GET /api/mis-reportes': pagina([EDITABLE, VALIDADO]) })
    renderizar()

    await screen.findByRole('heading', { name: 'BCH-2026-000002' })
    expect(screen.getAllByRole('link', { name: /^Editar/ })).toHaveLength(1)
    expect(screen.getByRole('link', { name: /Editar BCH-2026-000001/ })).toHaveAttribute('href', '/mis-reportes/1/editar')
    expect(screen.getAllByRole('button', { name: /^Eliminar/ })).toHaveLength(1)
  })

  it('eliminar pide confirmación: cancelar no borra y confirmar llama a DELETE y refresca la lista', async () => {
    const api = simularApi({
      'GET /api/mis-reportes': [pagina([EDITABLE, VALIDADO]), pagina([VALIDADO])],
      'DELETE /api/reportes/1': { status: 204 },
    })
    renderizar()
    const u = userEvent.setup()

    await u.click(await screen.findByRole('button', { name: /Eliminar BCH-2026-000001/ }))
    expect(screen.getByText(/¿Eliminar el reporte BCH-2026-000001\?/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toHaveFocus() // el foco va a la opción segura

    await u.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(api.de('DELETE /api/reportes/1')).toHaveLength(0)
    expect(screen.getByRole('button', { name: /Eliminar BCH-2026-000001/ })).toBeInTheDocument()

    await u.click(screen.getByRole('button', { name: /Eliminar BCH-2026-000001/ }))
    await u.click(screen.getByRole('button', { name: 'Sí, eliminar' }))

    expect(await screen.findByText('Se eliminó el reporte BCH-2026-000001.')).toBeInTheDocument()
    expect(api.de('DELETE /api/reportes/1')).toHaveLength(1)
    expect(screen.queryByRole('heading', { name: 'BCH-2026-000001' })).not.toBeInTheDocument()
  })

  it('si el reporte ya no está en Recibido (409) muestra el mensaje y refresca la lista', async () => {
    const api = simularApi({
      'GET /api/mis-reportes': [pagina([EDITABLE]), pagina([{ ...EDITABLE, estado: 'validado', puede_editar: false }])],
      'DELETE /api/reportes/1': {
        status: 409,
        cuerpo: { detail: 'El reporte ya fue validado y no se puede eliminar.', codigo: 'REPORTE_NO_EDITABLE' },
      },
    })
    renderizar()
    const u = userEvent.setup()

    await u.click(await screen.findByRole('button', { name: /Eliminar BCH-2026-000001/ }))
    await u.click(screen.getByRole('button', { name: 'Sí, eliminar' }))

    expect(await screen.findByText('El reporte ya fue validado y no se puede eliminar.')).toBeInTheDocument()
    expect(await screen.findByText('Estado: Validado')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Eliminar/ })).not.toBeInTheDocument()
    expect(api.de('GET /api/mis-reportes')).toHaveLength(2)
  })
})

describe('Editar un reporte (HU-02.5)', () => {
  const CATALOGOS: Record<string, RespuestaSimulada> = {
    'GET /api/tipos-dano': { cuerpo: TIPOS_DANO },
    'GET /api/colonias': { cuerpo: { items: COLONIAS, total: 2, pagina: 1, tam: 500 } },
  }

  it('abre el formulario precargado, guarda con PUT y regresa a la lista con un aviso', async () => {
    const api = simularApi({
      ...CATALOGOS,
      'GET /api/reportes/1': { cuerpo: { ...EDITABLE, longevidad_dias: 0, ultima_actividad: EDITABLE.creado_en, historial: [] } },
      'PUT /api/reportes/1': { cuerpo: { ...EDITABLE, tamano: 'mediano' } },
      'GET /api/mis-reportes': pagina([EDITABLE]),
    })
    renderizar('/mis-reportes/1/editar')
    const u = userEvent.setup()

    // Precargado con lo que ya tenía el reporte
    expect(await screen.findByLabelText(/Tipo de daño/)).toHaveValue('bache')
    expect(screen.getByLabelText(/Calle/)).toHaveValue('Av. Tecnológico')
    expect(screen.getByLabelText(/Tamaño/)).toHaveValue('grande')
    expect(screen.getByLabelText(/Latitud/)).toHaveValue('31.7001')

    await u.selectOptions(screen.getByLabelText(/Tamaño/), 'mediano')
    await u.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    expect(await screen.findByText('Se guardaron los cambios del reporte BCH-2026-000001.')).toBeInTheDocument()
    const cuerpo = api.de('PUT /api/reportes/1')[0].cuerpo
    expect(cuerpo).toMatchObject({ tamano: 'mediano', profundidad: 'media', carril: 'derecho', colonia_id: 12 })
    expect(cuerpo).not.toHaveProperty('forzar') // editar no usa la verificación de duplicados
  })

  it('un reporte que ya no está en Recibido no se puede editar', async () => {
    simularApi({
      ...CATALOGOS,
      'GET /api/reportes/2': { cuerpo: { ...VALIDADO, longevidad_dias: 1, ultima_actividad: VALIDADO.creado_en, historial: [] } },
    })
    renderizar('/mis-reportes/2/editar')

    expect(await screen.findByText(/ya no se puede editar/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Guardar cambios' })).not.toBeInTheDocument()
  })

  it('si el servidor responde 409 al guardar muestra el mensaje y conserva lo capturado', async () => {
    simularApi({
      ...CATALOGOS,
      'GET /api/reportes/1': { cuerpo: { ...EDITABLE, longevidad_dias: 0, ultima_actividad: EDITABLE.creado_en, historial: [] } },
      'PUT /api/reportes/1': {
        status: 409,
        cuerpo: { detail: 'Un moderador ya validó este reporte; no se puede editar.', codigo: 'REPORTE_NO_EDITABLE' },
      },
    })
    renderizar('/mis-reportes/1/editar')
    const u = userEvent.setup()

    await u.selectOptions(await screen.findByLabelText(/Tamaño/), 'chico')
    await u.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    expect(await screen.findByText(/Un moderador ya validó este reporte/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Tamaño/)).toHaveValue('chico')
  })

  it('un id inválido en la URL muestra un error sin llamar a la API', async () => {
    const api = simularApi(CATALOGOS)
    renderizar('/mis-reportes/abc/editar')

    expect(await screen.findByText('Ese reporte no existe.')).toBeInTheDocument()
    expect(api.llamadas.filter((l) => l.clave.startsWith('GET /api/reportes/'))).toHaveLength(0)
  })
})
