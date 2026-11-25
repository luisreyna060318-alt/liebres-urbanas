import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { authFalso, CIUDADANO, ConAuth, simularApi } from '../pruebas/ayudas.tsx'
import type { RespuestaSimulada } from '../pruebas/ayudas.tsx'
import { COLONIAS, reporteCercano, reporteMio, TIPOS_DANO } from '../pruebas/datos.ts'
import Reportar from './Reportar.tsx'

type Usuario = ReturnType<typeof userEvent.setup>

const CATALOGOS: Record<string, RespuestaSimulada> = {
  'GET /api/tipos-dano': { cuerpo: TIPOS_DANO },
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

// Elige "Bache" y espera a que cargue el formulario
async function abrirFormularioBache(u: Usuario) {
  await u.click(screen.getByRole('radio', { name: /Bache o daño en el pavimento/ }))
  await screen.findByLabelText(/Tipo de daño/)
}

// Captura la ubicación a mano (es lo que se hace cuando no se usa el buscador)
async function capturarUbicacion(u: Usuario) {
  await u.click(screen.getByRole('button', { name: 'Capturar la ubicación a mano' }))
  await u.type(screen.getByLabelText(/Calle/), 'Av. Tecnológico')
  await u.selectOptions(await screen.findByLabelText(/Colonia/), '12')
  await u.type(screen.getByLabelText(/Latitud/), '31.7001')
  await u.type(screen.getByLabelText(/Longitud/), '-106.4302')
}

// Un bache grande completo, listo para enviar
async function capturarBacheCompleto(u: Usuario) {
  await capturarUbicacion(u)
  await u.selectOptions(screen.getByLabelText(/Tipo de daño/), 'bache')
  await u.selectOptions(screen.getByLabelText(/Tamaño/), 'grande')
  await u.selectOptions(screen.getByLabelText(/Profundidad/), 'media')
  await u.selectOptions(screen.getByLabelText(/Carril afectado/), 'derecho')
}

const enviar = (u: Usuario) => u.click(screen.getByRole('button', { name: 'Enviar reporte' }))

describe('Reportar: elegir qué reportar', () => {
  it('no muestra ningún formulario hasta elegir qué reportar', async () => {
    simularApi(CATALOGOS)
    renderizar()

    expect(screen.queryByLabelText(/Tipo de daño/)).not.toBeInTheDocument()
    expect(screen.queryByRole('form', { name: /Reportar/ })).not.toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /Encharcamiento/ })).toBeEnabled()

    await abrirFormularioBache(userEvent.setup())
    expect(screen.getByRole('button', { name: 'Enviar reporte' })).toBeInTheDocument()
  })
})

describe('Reportar: formulario dinámico por tipo de daño (HU-02.2)', () => {
  it('bache: pide tamaño, profundidad y carril con las leyendas de tamaño', async () => {
    simularApi(CATALOGOS)
    renderizar()
    const u = userEvent.setup()
    await abrirFormularioBache(u)

    // Antes de elegir el tipo no aparece ningún campo del daño
    expect(screen.queryByLabelText(/Tamaño/)).not.toBeInTheDocument()

    await u.selectOptions(screen.getByLabelText(/Tipo de daño/), 'bache')
    expect(screen.getByLabelText(/Profundidad/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Carril afectado/)).toBeInTheDocument()
    const tamano = screen.getByLabelText(/Tamaño/)
    expect(within(tamano).getByRole('option', { name: 'Chico: menos de 30 cm' })).toBeInTheDocument()
    expect(within(tamano).getByRole('option', { name: 'Mediano: 30 cm a 1 m' })).toBeInTheDocument()
    expect(within(tamano).getByRole('option', { name: 'Grande: más de 1 m' })).toBeInTheDocument()
  })

  it('hundimiento y grieta: solo tamaño y carril', async () => {
    simularApi(CATALOGOS)
    renderizar()
    const u = userEvent.setup()
    await abrirFormularioBache(u)

    for (const tipo of ['hundimiento', 'grieta']) {
      await u.selectOptions(screen.getByLabelText(/Tipo de daño/), tipo)
      expect(screen.getByLabelText(/Tamaño/)).toBeInTheDocument()
      expect(screen.getByLabelText(/Carril afectado/)).toBeInTheDocument()
      expect(screen.queryByLabelText(/Profundidad/)).not.toBeInTheDocument()
    }
  })

  it('alcantarilla sin tapa: pregunta si está señalizado y avisa que la severidad será Alta', async () => {
    simularApi(CATALOGOS)
    renderizar()
    const u = userEvent.setup()
    await abrirFormularioBache(u)
    await u.selectOptions(screen.getByLabelText(/Tipo de daño/), 'alcantarilla_sin_tapa')

    expect(screen.getByRole('group', { name: /¿El punto está señalizado\?/ })).toBeInTheDocument()
    expect(screen.getByText(/severidad será Alta automáticamente/)).toBeInTheDocument()
    expect(screen.queryByLabelText(/Tamaño/)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/Carril afectado/)).not.toBeInTheDocument()
  })

  it('la descripción cuenta los caracteres con el límite que manda /reglas', async () => {
    simularApi(CATALOGOS, { descripcion_max: 120 })
    renderizar()
    const u = userEvent.setup()
    await abrirFormularioBache(u)

    const descripcion = screen.getByLabelText(/Descripción/)
    await u.type(descripcion, 'Hueco')
    expect(await screen.findByText(/5 de 120 caracteres/)).toBeInTheDocument()
    expect(descripcion).toHaveAttribute('maxlength', '120')
  })
})

describe('Reportar: validación', () => {
  it('con el formulario vacío muestra un mensaje junto a cada campo y no envía nada', async () => {
    const api = simularApi(CATALOGOS)
    renderizar()
    const u = userEvent.setup()
    await abrirFormularioBache(u)
    await enviar(u)

    expect(screen.getByLabelText(/Calle/)).toHaveAccessibleDescription(/Escribe la calle/)
    expect(screen.getByLabelText(/Colonia/)).toHaveAccessibleDescription(/Elige la colonia/)
    expect(screen.getByLabelText(/Latitud/)).toHaveAccessibleDescription(/Falta la latitud/)
    expect(screen.getByLabelText(/Tipo de daño/)).toHaveAccessibleDescription(/Elige el tipo de daño/)
    expect(api.de('POST /api/reportes/baches')).toHaveLength(0)
  })

  it('al elegir un bache sin completar sus campos pide tamaño, profundidad y carril', async () => {
    simularApi(CATALOGOS)
    renderizar()
    const u = userEvent.setup()
    await abrirFormularioBache(u)
    await capturarUbicacion(u)
    await u.selectOptions(screen.getByLabelText(/Tipo de daño/), 'bache')
    await enviar(u)

    expect(screen.getByLabelText(/Tamaño/)).toHaveAccessibleDescription(/Elige el tamaño/)
    expect(screen.getByLabelText(/Profundidad/)).toHaveAccessibleDescription(/Elige la profundidad/)
    expect(screen.getByLabelText(/Carril afectado/)).toHaveAccessibleDescription(/Elige el carril/)
  })
})

describe('Reportar: envío', () => {
  it('envío exitoso: manda los campos del contrato y muestra folio, hora de Juárez y estado Recibido', async () => {
    const api = simularApi({ ...CATALOGOS, 'POST /api/reportes/baches': { status: 201, cuerpo: reporteMio() } })
    renderizar()
    const u = userEvent.setup()
    await abrirFormularioBache(u)
    await capturarBacheCompleto(u)
    await u.type(screen.getByLabelText(/Descripción/), 'Hueco grande junto al semáforo')
    await enviar(u)

    expect(await screen.findByRole('heading', { name: 'Reporte enviado' })).toBeInTheDocument()
    expect(api.de('POST /api/reportes/baches')[0].cuerpo).toEqual({
      tipo_dano_codigo: 'bache',
      lat: 31.7001,
      lon: -106.4302,
      calle: 'Av. Tecnológico',
      colonia_id: 12,
      descripcion: 'Hueco grande junto al semáforo',
      tamano: 'grande',
      profundidad: 'media',
      carril: 'derecho',
      senalizado: null,
      forzar: false,
    })

    expect(screen.getByText('BCH-2026-000123')).toBeInTheDocument()
    // 21:05 UTC es 14:05 en Ciudad Juárez
    expect(screen.getByText(/24 nov 2026, 14:05 \(hora de Ciudad Juárez\)/)).toBeInTheDocument()
    expect(screen.getByText('Recibido')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ir a Mis reportes' })).toHaveAttribute('href', '/mis-reportes')
    expect(screen.getByRole('link', { name: 'Reportar otro' })).toHaveAttribute('href', '/reportar')
  })

  it('"Reportar otro" regresa a una pantalla limpia', async () => {
    simularApi({ ...CATALOGOS, 'POST /api/reportes/baches': { status: 201, cuerpo: reporteMio() } })
    renderizar()
    const u = userEvent.setup()
    await abrirFormularioBache(u)
    await capturarBacheCompleto(u)
    await enviar(u)
    await u.click(await screen.findByRole('link', { name: 'Reportar otro' }))

    expect(screen.getByRole('heading', { name: 'Reportar un problema' })).toBeInTheDocument()
    expect(screen.queryByLabelText(/Tipo de daño/)).not.toBeInTheDocument()
  })

  it('si falla la conexión NO se pierde lo capturado y se puede reenviar (HU-02.1 CA4)', async () => {
    const api = simularApi({
      ...CATALOGOS,
      'POST /api/reportes/baches': ['sin_red', { status: 201, cuerpo: reporteMio() }],
    })
    renderizar()
    const u = userEvent.setup()
    await abrirFormularioBache(u)
    await capturarBacheCompleto(u)
    await u.type(screen.getByLabelText(/Descripción/), 'Hueco profundo')
    await enviar(u)

    expect(await screen.findByText(/No se pudo conectar con el servidor. Tus datos siguen aquí/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Calle/)).toHaveValue('Av. Tecnológico')
    expect(screen.getByLabelText(/Tamaño/)).toHaveValue('grande')
    expect(screen.getByLabelText(/Descripción/)).toHaveValue('Hueco profundo')

    await enviar(u) // al volver la conexión basta con enviar otra vez
    expect(await screen.findByRole('heading', { name: 'Reporte enviado' })).toBeInTheDocument()
    expect(api.de('POST /api/reportes/baches')).toHaveLength(2)
  })

  it('422 FUERA_DEL_MUNICIPIO muestra un mensaje claro y conserva los datos', async () => {
    simularApi({
      ...CATALOGOS,
      'POST /api/reportes/baches': { status: 422, cuerpo: { detail: 'Fuera', codigo: 'FUERA_DEL_MUNICIPIO' } },
    })
    renderizar()
    const u = userEvent.setup()
    await abrirFormularioBache(u)
    await capturarBacheCompleto(u)
    await enviar(u)

    expect(await screen.findByText(/fuera de Ciudad Juárez/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Latitud/)).toHaveValue('31.7001')
  })

  it('429 LIMITE_HORARIO avisa el límite por hora', async () => {
    simularApi(
      { ...CATALOGOS, 'POST /api/reportes/baches': { status: 429, cuerpo: { detail: 'Límite', codigo: 'LIMITE_HORARIO' } } },
      { max_reportes_por_hora: 10 },
    )
    renderizar()
    const u = userEvent.setup()
    await abrirFormularioBache(u)
    await capturarBacheCompleto(u)
    await enviar(u)

    expect(await screen.findByText(/límite de 10 reportes por hora/)).toBeInTheDocument()
  })

  it('muestra junto a su campo los `campos` que devuelve el servidor', async () => {
    simularApi({
      ...CATALOGOS,
      'POST /api/reportes/baches': {
        status: 422,
        cuerpo: { detail: 'Revisa los datos.', codigo: 'VALIDACION', campos: { descripcion: 'El servidor rechazó la descripción.' } },
      },
    })
    renderizar()
    const u = userEvent.setup()
    await abrirFormularioBache(u)
    await capturarBacheCompleto(u)
    await enviar(u)

    expect(await screen.findByLabelText(/Descripción/)).toHaveAccessibleDescription(/El servidor rechazó la descripción/)
  })
})

describe('Reportar: posible duplicado (HU-02.3)', () => {
  const DUPLICADO = {
    status: 409,
    cuerpo: { detail: 'Hay un reporte cercano.', codigo: 'POSIBLE_DUPLICADO', duplicados: [reporteCercano()] },
  }

  it('muestra los reportes cercanos con folio, tipo con ícono y texto, estado, antigüedad y distancia', async () => {
    simularApi({ ...CATALOGOS, 'POST /api/reportes/baches': DUPLICADO })
    renderizar()
    const u = userEvent.setup()
    await abrirFormularioBache(u)
    await capturarBacheCompleto(u)
    await enviar(u)

    const aviso = await screen.findByRole('region', { name: '¿Es el mismo problema?' })
    expect(within(aviso).getByRole('heading', { name: 'BCH-2026-000050' })).toBeInTheDocument()
    expect(within(aviso).getByText(/Bache/)).toBeInTheDocument()
    expect(within(aviso).getByText('Estado: Recibido')).toBeInTheDocument()
    expect(within(aviso).getByText(/Hace 3 días · a 12 m/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Enviar reporte' })).not.toBeInTheDocument()
  })

  it('"Confirmar este reporte" suma una confirmación y no crea folio nuevo', async () => {
    const api = simularApi({
      ...CATALOGOS,
      'POST /api/reportes/baches': DUPLICADO,
      'POST /api/reportes/77/confirmaciones': { status: 201, cuerpo: { ...reporteCercano(), confirmaciones: 3 } },
    })
    renderizar()
    const u = userEvent.setup()
    await abrirFormularioBache(u)
    await capturarBacheCompleto(u)
    await enviar(u)
    await u.click(await screen.findByRole('button', { name: /Confirmar este reporte/ }))

    expect(await screen.findByRole('heading', { name: 'Gracias por confirmar' })).toBeInTheDocument()
    expect(screen.getByText(/No se creó un folio nuevo/)).toBeInTheDocument()
    expect(api.de('POST /api/reportes/77/confirmaciones')[0].cuerpo).toEqual({ tipo: 'confirma' })
    expect(api.de('POST /api/reportes/baches')).toHaveLength(1) // solo el primer intento
  })

  it('"Es un daño distinto, reportarlo de todos modos" reenvía con forzar: true', async () => {
    const api = simularApi({
      ...CATALOGOS,
      'POST /api/reportes/baches': [DUPLICADO, { status: 201, cuerpo: reporteMio({ folio: 'BCH-2026-000124' }) }],
    })
    renderizar()
    const u = userEvent.setup()
    await abrirFormularioBache(u)
    await capturarBacheCompleto(u)
    await enviar(u)
    await u.click(await screen.findByRole('button', { name: 'Es un daño distinto, reportarlo de todos modos' }))

    expect(await screen.findByText('BCH-2026-000124')).toBeInTheDocument()
    const envios = api.de('POST /api/reportes/baches')
    expect(envios).toHaveLength(2)
    expect(envios[0].cuerpo).toMatchObject({ forzar: false })
    expect(envios[1].cuerpo).toMatchObject({ forzar: true })
  })

  it('si ya habías confirmado ese reporte lo dice y deja elegir otra acción', async () => {
    simularApi({
      ...CATALOGOS,
      'POST /api/reportes/baches': DUPLICADO,
      'POST /api/reportes/77/confirmaciones': { status: 409, cuerpo: { detail: 'Ya', codigo: 'YA_CONFIRMADO' } },
    })
    renderizar()
    const u = userEvent.setup()
    await abrirFormularioBache(u)
    await capturarBacheCompleto(u)
    await enviar(u)
    await u.click(await screen.findByRole('button', { name: /Confirmar este reporte/ }))

    expect(await screen.findByText('Ya respondiste sobre este reporte.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Es un daño distinto, reportarlo de todos modos' })).toBeEnabled()
  })

  it('"Volver a mis datos" regresa al formulario con todo lo capturado', async () => {
    simularApi({ ...CATALOGOS, 'POST /api/reportes/baches': DUPLICADO })
    renderizar()
    const u = userEvent.setup()
    await abrirFormularioBache(u)
    await capturarBacheCompleto(u)
    await enviar(u)
    await u.click(await screen.findByRole('button', { name: 'Volver a mis datos' }))

    expect(screen.getByRole('button', { name: 'Enviar reporte' })).toBeInTheDocument()
    expect(screen.getByLabelText(/Calle/)).toHaveValue('Av. Tecnológico')
  })
})
