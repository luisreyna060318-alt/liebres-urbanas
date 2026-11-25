import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import type { Tablero as DatosTablero } from '../api/tipos.ts'
import { etiquetaSemana, topeEscala } from '../utils/grafica.ts'
import { authFalso, ConAuth, COORDINADOR, simularApi } from '../pruebas/ayudas.tsx'
import type { RespuestaSimulada } from '../pruebas/ayudas.tsx'
import Tablero from './Tablero.tsx'

const SEMANAS = Array.from({ length: 12 }, (_, i) => ({
  inicio: `2026-${i < 4 ? '09' : i < 8 ? '10' : '11'}-0${(i % 4) + 1}`,
  total: i === 11 ? 7 : i === 6 ? 3 : 0,
}))

function tablero(parcial: Partial<DatosTablero> = {}): DatosTablero {
  return {
    filtro: { desde: null, hasta: null, sector_id: null },
    totales: {
      total: 10,
      bache: 7,
      encharcamiento: 3,
      rechazados: 2,
      por_estado: [
        { categoria: 'bache', estado: 'recibido', total: 3 },
        { categoria: 'bache', estado: 'validado', total: 2 },
        { categoria: 'bache', estado: 'en_reparacion', total: 1 },
        { categoria: 'bache', estado: 'reparado', total: 1 },
        { categoria: 'encharcamiento', estado: 'activo', total: 1 },
        { categoria: 'encharcamiento', estado: 'historico', total: 2 },
      ],
    },
    top_colonias: [
      { colonia: { id: 1, nombre: 'Partido Escobedo' }, abiertos: 4 },
      { colonia: { id: 2, nombre: 'Colonia Lejana' }, abiertos: 2 },
    ],
    tiempo_promedio_reparacion_dias: 3.5,
    reparados_medidos: 1,
    por_semana: SEMANAS,
    mas_longevos: [
      {
        id: 45,
        folio: 'BCH-2026-000045',
        calle: 'Calle Ficticia',
        colonia: { id: 1, nombre: 'Partido Escobedo' },
        estado: 'validado',
        antiguedad_dias: 30,
      },
    ],
    longevidad_por_colonia: [{ colonia: { id: 1, nombre: 'Partido Escobedo' }, abiertos: 4, promedio_dias: 12.5 }],
    ...parcial,
  }
}

const SECTORES: RespuestaSimulada = {
  cuerpo: [
    { id: 1, nombre: 'Centro' },
    { id: 2, nombre: 'Sur' },
  ],
}

function renderizar() {
  return render(
    <ConAuth valor={authFalso({ usuario: COORDINADOR })}>
      <MemoryRouter>
        <Tablero />
      </MemoryRouter>
    </ConAuth>,
  )
}

describe('Tablero de indicadores (HU-07.1)', () => {
  it('muestra "cargando" y luego los totales con texto, las tablas y el enlace al detalle', async () => {
    simularApi({ 'GET /api/tablero': { cuerpo: tablero() }, 'GET /api/sectores': SECTORES })
    renderizar()

    expect(screen.getByText('Cargando indicadores…')).toBeInTheDocument()
    expect(await screen.findByText('reportes en total')).toBeInTheDocument()
    expect(screen.getByText(/rechazados \(no suman en el total\)/)).toHaveTextContent('2')
    expect(screen.getByText('3.5 días')).toBeInTheDocument()

    const baches = screen.getByRole('heading', { name: 'Bache por estado' }).parentElement!
    expect(within(baches).getByText('En reparación')).toBeInTheDocument()
    const charcos = screen.getByRole('heading', { name: 'Encharcamiento por estado' }).parentElement!
    expect(within(charcos).getByText('Histórico').nextSibling).toHaveTextContent('2')

    const top = screen.getByRole('table', { name: /10 colonias con más baches/ })
    expect(within(top).getAllByRole('row')).toHaveLength(3)
    expect(within(top).getByRole('row', { name: /1 Partido Escobedo 4/ })).toBeInTheDocument()

    const longevos = screen.getByRole('table', { name: /baches abiertos con más días/ })
    expect(within(longevos).getByRole('link', { name: 'BCH-2026-000045' })).toHaveAttribute('href', '/reportes/45')
    expect(within(longevos).getByText('30 días')).toBeInTheDocument()
    expect(screen.getByRole('table', { name: /promedio de los baches abiertos/ })).toHaveTextContent('12.5 días')
  })

  it('dibuja la gráfica semanal accesible y su tabla con los mismos datos', async () => {
    simularApi({ 'GET /api/tablero': { cuerpo: tablero() }, 'GET /api/sectores': SECTORES })
    renderizar()

    const grafica = await screen.findByRole('img', { name: /Reportes creados por semana/ })
    expect(grafica.querySelector('title')).toHaveTextContent('Reportes creados por semana')
    expect(grafica.querySelector('desc')).toHaveTextContent('10 reportes')
    const barras = grafica.querySelectorAll('rect')
    expect(barras).toHaveLength(12)
    // Escala: el tope es 10 (máximo 7); la barra de 7 mide 7/10 de la de 3 * 10/3
    const alto = (i: number) => Number(barras[i].getAttribute('height'))
    expect(alto(0)).toBe(0)
    expect(alto(11) / alto(6)).toBeCloseTo(7 / 3)

    const tabla = screen.getByRole('table', { name: /Reportes por semana/ })
    const filas = within(tabla).getAllByRole('row').slice(1)
    expect(filas).toHaveLength(12)
    expect(filas[11]).toHaveTextContent(`${etiquetaSemana(SEMANAS[11].inicio)}7`)
    expect(screen.getByRole('region', { name: /Gráfica de reportes por semana/ })).toHaveAttribute('tabindex', '0')
  })

  it('si falla muestra el error y deja reintentar', async () => {
    simularApi({ 'GET /api/tablero': ['sin_red', { cuerpo: tablero() }], 'GET /api/sectores': SECTORES })
    renderizar()

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByText('reportes en total')).toBeInTheDocument()
  })

  it('sin reportes muestra el mensaje de vacío', async () => {
    const vacio = tablero({
      totales: { total: 0, bache: 0, encharcamiento: 0, rechazados: 0, por_estado: [] },
      top_colonias: [],
      mas_longevos: [],
      longevidad_por_colonia: [],
      tiempo_promedio_reparacion_dias: null,
      reparados_medidos: 0,
    })
    simularApi({ 'GET /api/tablero': { cuerpo: vacio }, 'GET /api/sectores': SECTORES })
    renderizar()

    expect(await screen.findByText(/No hay reportes con estos filtros/)).toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })

  it('aplica los filtros de fecha y sector y valida el rango antes de pedir', async () => {
    const api = simularApi({ 'GET /api/tablero': { cuerpo: tablero() }, 'GET /api/sectores': SECTORES })
    renderizar()
    await screen.findByText('reportes en total')
    await screen.findByRole('option', { name: 'Sur' })

    await userEvent.type(screen.getByLabelText('Desde'), '2026-11-10')
    await userEvent.type(screen.getByLabelText('Hasta'), '2026-11-01')
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar' }))
    expect(screen.getByText('La fecha final no puede ser anterior a la inicial')).toBeInTheDocument()
    expect(api.de('GET /api/tablero')).toHaveLength(1)

    await userEvent.clear(screen.getByLabelText('Hasta'))
    await userEvent.type(screen.getByLabelText('Hasta'), '2026-11-20')
    await userEvent.selectOptions(screen.getByLabelText('Sector'), 'Sur')
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar' }))
    await screen.findByText('reportes en total')
    const ultima = api.de('GET /api/tablero').at(-1)!.url.searchParams
    expect([ultima.get('desde'), ultima.get('hasta'), ultima.get('sector_id')]).toEqual(['2026-11-10', '2026-11-20', '2'])

    await userEvent.click(screen.getByRole('button', { name: 'Limpiar filtros' }))
    await screen.findByText('reportes en total')
    expect(api.de('GET /api/tablero').at(-1)!.url.search).toBe('')
  })
})

describe('GraficaSemanal: utilidades', () => {
  it('redondea el tope de la escala y escribe la semana', () => {
    expect([topeEscala(0), topeEscala(7), topeEscala(10), topeEscala(23), topeEscala(120)]).toEqual([1, 10, 10, 50, 200])
    expect(etiquetaSemana('2026-09-07')).toBe('7 sep')
  })
})
