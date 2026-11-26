import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import type { ReporteDetalle } from '../api/tipos.ts'
import { authFalso, CIUDADANO, ConAuth, simularApi } from '../pruebas/ayudas.tsx'
import { encharcamientoMio, reporteMio } from '../pruebas/datos.ts'
import DetalleReporte from './DetalleReporte.tsx'

function detalle(parcial: Partial<ReporteDetalle> = {}, base = reporteMio()): ReporteDetalle {
  const { puede_editar: _a, motivo_rechazo: _b, ...publico } = base
  return {
    ...publico,
    estado: 'validado',
    sin_validar: false,
    confirmaciones: 3,
    antiguedad_dias: 5,
    longevidad_dias: 5,
    ultima_actividad: '2026-11-25T17:00:00Z',
    ultima_confirmacion: '2026-11-25T03:30:00Z', // 24 nov a las 20:30 en Juárez
    historial: [
      { estado_anterior: 'recibido', estado_nuevo: 'validado', comentario: 'Confirmado en sitio', creado_en: '2026-11-25T17:00:00Z' },
      { estado_anterior: null, estado_nuevo: 'recibido', comentario: null, creado_en: '2026-11-24T21:05:00Z' },
    ],
    ...parcial,
  }
}

function renderizar(ruta = '/reportes/345', auth = authFalso()) {
  return render(
    <ConAuth valor={auth}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/reportes/:id" element={<DetalleReporte />} />
          <Route path="/" element={<p>Pantalla de consulta</p>} />
        </Routes>
      </MemoryRouter>
    </ConAuth>,
  )
}

describe('Detalle de un reporte (HU-04.4)', () => {
  it('muestra cargando y luego folio, tipo, ubicación, datos del daño, confirmaciones y estado', async () => {
    simularApi({ 'GET /api/reportes/345': { cuerpo: detalle() } })
    renderizar()

    expect(screen.getByText('Cargando el reporte…')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { level: 1, name: 'Reporte BCH-2026-000123' })).toBeInTheDocument()
    // Tipo con ícono decorativo Y texto (la información no depende del ícono ni del color)
    expect(document.querySelector('.tarjeta-reporte-tipo')).toHaveTextContent('🚧 Bache')
    expect(screen.getByText('Estado: Validado')).toBeInTheDocument()
    const datos = screen.getByRole('heading', { name: 'Datos del reporte' }).nextElementSibling as HTMLElement
    const valor = (termino: string) => within(datos).getByText(termino).nextElementSibling
    expect(valor('Ubicación')).toHaveTextContent('Av. Tecnológico, Partido Escobedo')
    expect(valor('Tamaño')).toHaveTextContent('Grande: más de 1 m')
    expect(valor('Carril')).toHaveTextContent('Carril derecho')
    expect(valor('Severidad')).toHaveTextContent('Alta')
    expect(valor('Confirmaciones')).toHaveTextContent('3')
  })

  it('en un bache el tipo de daño aparece una sola vez (en los datos, no repetido bajo el encabezado)', async () => {
    simularApi({
      'GET /api/reportes/345': { cuerpo: detalle({ tipo_dano: { codigo: 'grieta', nombre: 'Grieta' } }) },
    })
    renderizar()

    await screen.findByRole('heading', { level: 1, name: /BCH-2026-000123/ })
    expect(document.querySelector('.tarjeta-reporte-tipo')).not.toHaveTextContent('Grieta')
    expect(screen.getAllByText('Grieta')).toHaveLength(1)
    expect(screen.getByText('Tipo de daño').nextElementSibling).toHaveTextContent('Grieta')
  })

  it('en baches muestra la fecha original, la longevidad y la última confirmación en hora de Juárez', async () => {
    simularApi({ 'GET /api/reportes/345': { cuerpo: detalle() } })
    renderizar()

    await screen.findByRole('heading', { level: 1, name: /BCH-2026-000123/ })
    expect(screen.getByText('Reportado el').nextElementSibling).toHaveTextContent('24 nov 2026, 14:05')
    expect(screen.getByText('Longevidad').nextElementSibling).toHaveTextContent('5 días sin reparar')
    expect(screen.getByText('Última confirmación').nextElementSibling).toHaveTextContent('24 nov 2026, 20:30')
  })

  it('el historial va del más reciente al más antiguo, con comentario y sin quién hizo el cambio', async () => {
    simularApi({ 'GET /api/reportes/345': { cuerpo: detalle() } })
    renderizar()

    const lista = (await screen.findByRole('heading', { name: 'Historial' })).nextElementSibling as HTMLElement
    const pasos = within(lista).getAllByRole('listitem')
    expect(pasos[0]).toHaveTextContent('25 nov 2026, 10:00 · Pasó de Recibido a Validado')
    expect(pasos[0]).toHaveTextContent('Confirmado en sitio')
    expect(pasos[1]).toHaveTextContent('24 nov 2026, 14:05 · Se reportó como Recibido')
  })

  it('un bache reparado muestra la fecha de reparación y la longevidad hasta ese día', async () => {
    simularApi({
      'GET /api/reportes/345': { cuerpo: detalle({ estado: 'reparado', fecha_reparacion: '2026-11-20', longevidad_dias: 7, ultima_confirmacion: null }) },
    })
    renderizar()

    await screen.findByRole('heading', { level: 1, name: /BCH-2026-000123/ })
    expect(screen.getByText('Reparado el').nextElementSibling).toHaveTextContent('20 nov 2026')
    expect(screen.getByText('Longevidad').nextElementSibling).toHaveTextContent('7 días (hasta su reparación)')
    expect(screen.getByText('Última confirmación').nextElementSibling).toHaveTextContent('Nadie lo ha confirmado todavía')
  })

  it('un encharcamiento muestra el nivel del agua y la vigencia, sin datos de bache', async () => {
    simularApi({ 'GET /api/reportes/500': { cuerpo: detalle({ estado: 'activo', historial: [] }, encharcamientoMio()) } })
    renderizar('/reportes/500')

    await screen.findByRole('heading', { level: 1, name: 'Reporte ENC-2026-000045' })
    expect(screen.getByText(/^Encharcamiento/)).toBeInTheDocument()
    expect(screen.getByText('Nivel del agua').nextElementSibling).toHaveTextContent('A media llanta')
    expect(screen.getByText('Vigente hasta').nextElementSibling).toHaveTextContent('24 nov 2026, 20:05')
    expect(screen.queryByText('Longevidad')).not.toBeInTheDocument()
    expect(screen.getByText('Todavía no hay cambios registrados.')).toBeInTheDocument()
  })

  it('un 404 muestra un mensaje amable con enlace de regreso a la consulta', async () => {
    simularApi({ 'GET /api/reportes/9': { status: 404, cuerpo: { detail: 'El reporte no existe', codigo: 'NO_ENCONTRADO' } } })
    renderizar('/reportes/9')

    expect(await screen.findByText('Este reporte no existe o ya no está disponible.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: 'Detalle del reporte' })).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('link', { name: 'Volver a los reportes' }))
    expect(await screen.findByText('Pantalla de consulta')).toBeInTheDocument()
  })

  it('un id que no es número no llama a la API', async () => {
    const api = simularApi({})
    renderizar('/reportes/abc')

    expect(await screen.findByText('Este reporte no existe o ya no está disponible.')).toBeInTheDocument()
    expect(api.llamadas.filter((l) => l.clave.startsWith('GET /api/reportes'))).toHaveLength(0)
  })

  it('si falla la red muestra el error y deja reintentar', async () => {
    simularApi({ 'GET /api/reportes/345': ['sin_red', { cuerpo: detalle() }] })
    renderizar()

    expect(await screen.findByText(/No se pudo conectar con el servidor/)).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByRole('heading', { level: 1, name: /BCH-2026-000123/ })).toBeInTheDocument()
  })
})

describe('Confirmar o desmentir desde el detalle (HU-03.3 y HU-02.3)', () => {
  const comoCiudadano = () => authFalso({ usuario: CIUDADANO })
  const activo = () => detalle({ estado: 'activo', historial: [] }, encharcamientoMio())

  it('un encharcamiento activo ofrece "Sigue ahí" y "Ya no hay agua" y registra la respuesta', async () => {
    const api = simularApi({
      'GET /api/reportes/500': [{ cuerpo: activo() }, { cuerpo: { ...activo(), estado: 'historico' } }],
      'POST /api/reportes/500/confirmaciones': { status: 201, cuerpo: { ...activo(), estado: 'historico' } },
    })
    renderizar('/reportes/500', comoCiudadano())

    expect(await screen.findByRole('button', { name: 'Sigue ahí' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Ya no hay agua' }))

    expect(await screen.findByText(/Registramos que ya no hay agua/)).toBeInTheDocument()
    expect(api.de('POST /api/reportes/500/confirmaciones')[0].cuerpo).toEqual({ tipo: 'ya_no_hay' })
    // El reporte pasó a Histórico: se actualiza el estado y desaparecen los botones
    expect(await screen.findByText('Estado: Histórico')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ya no hay agua' })).not.toBeInTheDocument()
  })

  it('un bache abierto se puede confirmar y se actualiza el contador', async () => {
    simularApi({
      'GET /api/reportes/345': [{ cuerpo: detalle() }, { cuerpo: detalle({ confirmaciones: 4 }) }],
      'POST /api/reportes/345/confirmaciones': { status: 201, cuerpo: detalle({ confirmaciones: 4 }) },
    })
    renderizar('/reportes/345', comoCiudadano())

    await userEvent.click(await screen.findByRole('button', { name: 'Confirmar que sigue ahí' }))

    expect(await screen.findByText(/Confirmaste este reporte/)).toBeInTheDocument()
    expect(screen.getByText('Confirmaciones').nextElementSibling).toHaveTextContent('4')
  })

  it('sin sesión invita a iniciar sesión y un reporte reparado no ofrece confirmar', async () => {
    simularApi({ 'GET /api/reportes/345': { cuerpo: detalle() } })
    const { unmount } = renderizar()
    expect(await screen.findByRole('link', { name: 'inicia sesión' })).toBeInTheDocument()
    unmount()

    simularApi({ 'GET /api/reportes/345': { cuerpo: detalle({ estado: 'reparado' }) } })
    renderizar('/reportes/345', comoCiudadano())
    await screen.findByText('Estado: Reparado')
    expect(screen.queryByRole('button', { name: 'Confirmar que sigue ahí' })).not.toBeInTheDocument()
  })
})
