import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import type { UsuarioAdmin } from '../api/tipos.ts'
import { authFalso, COORDINADOR, ConAuth, simularApi } from '../pruebas/ayudas.tsx'
import type { RespuestaSimulada } from '../pruebas/ayudas.tsx'
import AdminUsuarios from './AdminUsuarios.tsx'

function cuenta(id: number, nombre: string, extra: Partial<UsuarioAdmin> = {}): UsuarioAdmin {
  return {
    id,
    nombre,
    correo: `${nombre.split(' ')[0].toLowerCase()}@ejemplo.test`,
    rol: 'ciudadano',
    activo: true,
    creado_en: '2026-11-24T21:05:00Z',
    ...extra,
  }
}

const ANA = cuenta(1, 'Ana Pérez')
const LUIS = cuenta(2, 'Luis Ríos', { rol: 'moderador' })
const MARTA = cuenta(3, 'Marta Soto', { activo: false })
const CLARA = cuenta(COORDINADOR.id, 'Clara Soto', { rol: 'coordinador' })

function pagina(items: UsuarioAdmin[], total = items.length, numero = 1): RespuestaSimulada {
  return { cuerpo: { items, total, pagina: numero, tam: 10 } }
}

function renderizar() {
  return render(
    <ConAuth valor={authFalso({ usuario: COORDINADOR })}>
      <MemoryRouter>
        <AdminUsuarios />
      </MemoryRouter>
    </ConAuth>,
  )
}

describe('Administrar usuarios (HU-06.2)', () => {
  it('lista las cuentas en una tabla accesible con rol, estado y alta', async () => {
    simularApi({ 'GET /api/usuarios': pagina([ANA, LUIS, MARTA, CLARA]) })
    renderizar()

    const fila = await screen.findByRole('row', { name: /Ana Pérez/ })
    expect(within(fila).getByText('ana@ejemplo.test')).toBeInTheDocument()
    expect(within(fila).getByText('Activa')).toBeInTheDocument()
    expect(within(fila).getByText('24 nov 2026')).toBeInTheDocument()
    expect(within(fila).getByLabelText('Rol de Ana Pérez')).toHaveValue('ciudadano')
    expect(within(screen.getByRole('row', { name: /Luis Ríos/ })).getByLabelText('Rol de Luis Ríos')).toHaveValue('moderador')
    expect(within(screen.getByRole('row', { name: /Marta Soto/ })).getByText('Suspendida')).toBeInTheDocument()
    expect(screen.getByRole('rowheader', { name: /Clara Soto \(tú\)/ })).toBeInTheDocument()
    for (const encabezado of screen.getAllByRole('columnheader')) expect(encabezado).toHaveAttribute('scope', 'col')
  })

  it('sin resultados muestra el vacío y si falla deja reintentar', async () => {
    simularApi({ 'GET /api/usuarios': ['sin_red', pagina([])] })
    renderizar()

    expect(await screen.findByText(/No se pudo conectar con el servidor/)).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByText('Aún no hay usuarios.')).toBeInTheDocument()
  })

  it('busca por nombre o correo y filtra por rol volviendo a la página 1', async () => {
    const api = simularApi({ 'GET /api/usuarios': pagina([ANA]) })
    renderizar()
    const u = userEvent.setup()

    await screen.findByRole('row', { name: /Ana Pérez/ })
    await u.type(screen.getByLabelText('Buscar por nombre o correo'), 'ana')
    await u.click(screen.getByRole('button', { name: 'Buscar' }))
    await u.selectOptions(screen.getByLabelText('Rol'), 'moderador')

    const ultima = api.de('GET /api/usuarios').at(-1)!.url.searchParams
    expect(ultima.get('q')).toBe('ana')
    expect(ultima.get('rol')).toBe('moderador')
    expect(ultima.get('pagina')).toBe('1')
    expect(ultima.get('tam')).toBe('10')
  })

  it('con filtros sin resultados lo dice', async () => {
    simularApi({ 'GET /api/usuarios': [pagina([ANA]), pagina([])] })
    renderizar()
    const u = userEvent.setup()

    await screen.findByRole('row', { name: /Ana Pérez/ })
    await u.type(screen.getByLabelText('Buscar por nombre o correo'), 'zzz')
    await u.click(screen.getByRole('button', { name: 'Buscar' }))
    expect(await screen.findByText('No hay usuarios con esos filtros.')).toBeInTheDocument()
  })

  it('pagina de 10 en 10', async () => {
    const api = simularApi({
      'GET /api/usuarios': ({ url }) => (url.searchParams.get('pagina') === '2' ? pagina([LUIS], 11, 2) : pagina([ANA], 11, 1)),
    })
    renderizar()

    expect(await screen.findByText('Página 1 de 2 (11 resultados)')).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(await screen.findByRole('row', { name: /Luis Ríos/ })).toBeInTheDocument()
    expect(api.de('GET /api/usuarios').map((l) => l.url.searchParams.get('pagina'))).toEqual(['1', '2'])
  })

  it('cambiar el rol pide confirmación: cancelar no cambia y confirmar llama a PUT /rol', async () => {
    const api = simularApi({
      'GET /api/usuarios': [pagina([ANA]), pagina([{ ...ANA, rol: 'moderador' }])],
      'PUT /api/usuarios/1/rol': { cuerpo: { ...ANA, rol: 'moderador' } },
    })
    renderizar()
    const u = userEvent.setup()

    // Elegir el rol en el select no pregunta nada: la pregunta sale con "Cambiar rol"
    await u.selectOptions(await screen.findByLabelText('Rol de Ana Pérez'), 'moderador')
    expect(screen.queryByText(/¿Cambiar el rol/)).not.toBeInTheDocument()
    expect(screen.getByLabelText('Rol de Ana Pérez')).toHaveValue('moderador')
    await u.click(screen.getByRole('button', { name: 'Cambiar rol de Ana Pérez' }))
    expect(screen.getByText('¿Cambiar el rol de Ana Pérez a moderador?')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toHaveFocus()
    await u.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(api.de('PUT /api/usuarios/1/rol')).toHaveLength(0)
    expect(screen.getByLabelText('Rol de Ana Pérez')).toHaveValue('ciudadano')

    await u.selectOptions(screen.getByLabelText('Rol de Ana Pérez'), 'moderador')
    await u.click(screen.getByRole('button', { name: 'Cambiar rol de Ana Pérez' }))
    await u.click(screen.getByRole('button', { name: 'Sí, confirmar' }))

    expect(await screen.findByText('Ana Pérez ahora es moderador.')).toBeInTheDocument()
    expect(api.de('PUT /api/usuarios/1/rol')[0].cuerpo).toEqual({ rol: 'moderador' })
    expect(screen.getByLabelText('Rol de Ana Pérez')).toHaveValue('moderador')
  })

  it('con teclado, las flechas del select no abren la confirmación y "Cambiar rol" solo sirve con un rol distinto', async () => {
    const api = simularApi({ 'GET /api/usuarios': pagina([ANA]) })
    renderizar()

    const select = await screen.findByLabelText('Rol de Ana Pérez')
    const boton = screen.getByRole('button', { name: 'Cambiar rol de Ana Pérez' })
    expect(boton).toBeDisabled() // el rol elegido es el que ya tiene

    select.focus()
    // jsdom no mueve el select con las flechas; este evento "change" es lo que el navegador dispara al hacerlo
    fireEvent.change(select, { target: { value: 'moderador' } })
    expect(select).toHaveFocus() // el foco no se va a la pregunta
    expect(screen.queryByRole('group', { name: 'Confirmar el cambio' })).not.toBeInTheDocument()
    expect(select).toHaveValue('moderador')
    expect(boton).toBeEnabled()
    expect(api.de('PUT /api/usuarios/1/rol')).toHaveLength(0)
  })

  it('suspender pide confirmación y llama a PUT /suspension con suspendido true', async () => {
    const api = simularApi({
      'GET /api/usuarios': [pagina([ANA]), pagina([{ ...ANA, activo: false }])],
      'PUT /api/usuarios/1/suspension': { cuerpo: { ...ANA, activo: false } },
    })
    renderizar()
    const u = userEvent.setup()

    await u.click(await screen.findByRole('button', { name: /Suspender a Ana Pérez/ }))
    expect(screen.getByText(/¿Suspender la cuenta de Ana Pérez\?/)).toBeInTheDocument()
    await u.click(screen.getByRole('button', { name: 'Sí, confirmar' }))

    expect(await screen.findByText('La cuenta de Ana Pérez quedó suspendida.')).toBeInTheDocument()
    expect(api.de('PUT /api/usuarios/1/suspension')[0].cuerpo).toEqual({ suspendido: true })
    expect(await screen.findByText('Suspendida')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Reactivar a Ana Pérez/ })).toBeInTheDocument()
  })

  it('reactivar una cuenta suspendida envía suspendido false', async () => {
    const api = simularApi({
      'GET /api/usuarios': pagina([MARTA]),
      'PUT /api/usuarios/3/suspension': { cuerpo: { ...MARTA, activo: true } },
    })
    renderizar()
    const u = userEvent.setup()

    await u.click(await screen.findByRole('button', { name: /Reactivar a Marta Soto/ }))
    expect(screen.getByText('¿Reactivar la cuenta de Marta Soto?')).toBeInTheDocument()
    await u.click(screen.getByRole('button', { name: 'Sí, confirmar' }))

    expect(await screen.findByText('La cuenta de Marta Soto quedó reactivada.')).toBeInTheDocument()
    expect(api.de('PUT /api/usuarios/3/suspension')[0].cuerpo).toEqual({ suspendido: false })
  })

  it('muestra el mensaje del servidor cuando es el último coordinador (409) y la cuenta no cambia', async () => {
    simularApi({
      'GET /api/usuarios': pagina([CLARA]),
      'PUT /api/usuarios/3/rol': {
        status: 409,
        cuerpo: {
          detail: 'Es el último coordinador activo. Nombra o reactiva a otro coordinador antes de quitarle el rol o suspenderlo',
          codigo: 'ULTIMO_COORDINADOR',
        },
      },
      'PUT /api/usuarios/3/suspension': {
        status: 409,
        cuerpo: { detail: 'Es el último coordinador activo. Nombra o reactiva a otro coordinador.', codigo: 'ULTIMO_COORDINADOR' },
      },
    })
    renderizar()
    const u = userEvent.setup()

    await u.selectOptions(await screen.findByLabelText('Rol de Clara Soto'), 'ciudadano')
    await u.click(screen.getByRole('button', { name: 'Cambiar rol de Clara Soto' }))
    await u.click(screen.getByRole('button', { name: 'Sí, confirmar' }))
    expect(await screen.findByText(/Es el último coordinador activo.*quitarle el rol/)).toBeInTheDocument()
    expect(await screen.findByLabelText('Rol de Clara Soto')).toHaveValue('coordinador')

    await u.click(screen.getByRole('button', { name: /Suspender a Clara Soto/ }))
    await u.click(screen.getByRole('button', { name: 'Sí, confirmar' }))
    expect(await screen.findByText('Es el último coordinador activo. Nombra o reactiva a otro coordinador.')).toBeInTheDocument()
    expect(screen.getByText('Activa')).toBeInTheDocument()
  })
})
