import { describe, expect, it, vi } from 'vitest'
import { respuestaJson, simularFetch } from '../pruebas/ayudas.tsx'
import { api, armarConsulta, ErrorApi, peticion, registrarAlExpirarSesion } from './cliente.ts'
import { guardarSesion, leerToken } from './sesion.ts'

const USUARIO = { id: 1, nombre: 'Ana', correo: 'ana@ejemplo.test', rol: 'ciudadano' } as const

describe('peticion', () => {
  it('manda el token Bearer y el cuerpo en JSON', async () => {
    guardarSesion('token-de-prueba', USUARIO)
    const fetchSimulado = simularFetch([respuestaJson({ ok: true })])

    await api.post('/api/algo', { a: 1 })

    const [url, opciones] = fetchSimulado.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toMatch(/\/api\/algo$/)
    expect(opciones.method).toBe('POST')
    expect((opciones.headers as Record<string, string>).Authorization).toBe('Bearer token-de-prueba')
    expect(opciones.body).toBe('{"a":1}')
  })

  it('convierte el cuerpo de error del contrato en un ErrorApi', async () => {
    simularFetch([
      respuestaJson(
        { detail: 'Revisa los datos.', codigo: 'VALIDACION', campos: { password: 'Muy corta.' } },
        422,
      ),
    ])

    const error = await peticion('/api/auth/registro', { metodo: 'POST', cuerpo: {} }).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ErrorApi)
    expect(error).toMatchObject({ status: 422, codigo: 'VALIDACION', detail: 'Revisa los datos.', message: 'Revisa los datos.' })
    expect((error as ErrorApi).campos).toEqual({ password: 'Muy corta.' })
  })

  it('un 401 NO_AUTENTICADO borra la sesión y avisa para cerrarla', async () => {
    guardarSesion('token-vencido', USUARIO)
    const alExpirar = vi.fn()
    registrarAlExpirarSesion(alExpirar)
    simularFetch([respuestaJson({ detail: 'Tu sesión caducó.', codigo: 'NO_AUTENTICADO' }, 401)])

    await expect(api.get('/api/auth/yo')).rejects.toBeInstanceOf(ErrorApi)

    expect(alExpirar).toHaveBeenCalledTimes(1)
    expect(leerToken()).toBeNull()
    registrarAlExpirarSesion(null)
  })

  it('un 401 CREDENCIALES (login fallido) no cierra ninguna sesión', async () => {
    const alExpirar = vi.fn()
    registrarAlExpirarSesion(alExpirar)
    simularFetch([respuestaJson({ detail: 'Correo o contraseña incorrectos.', codigo: 'CREDENCIALES' }, 401)])

    const error = await api.post('/api/auth/login', {}).catch((e: unknown) => e)

    expect(error).toMatchObject({ status: 401, codigo: 'CREDENCIALES', detail: 'Correo o contraseña incorrectos.' })
    expect(alExpirar).not.toHaveBeenCalled()
    registrarAlExpirarSesion(null)
  })

  it('sin red lanza un ErrorApi con estado 0 y mensaje en español', async () => {
    simularFetch() // sin respuestas: fetch falla

    const error = await api.get('/api/reglas-que-no-existe').catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ErrorApi)
    expect((error as ErrorApi).status).toBe(0)
    expect((error as ErrorApi).detail).toMatch(/No se pudo conectar/)
  })

  it('un 204 devuelve undefined', async () => {
    simularFetch([new Response(null, { status: 204 })])
    await expect(api.delete('/api/reportes/1')).resolves.toBeUndefined()
  })
})

describe('armarConsulta', () => {
  it('omite los valores vacíos', () => {
    expect(armarConsulta({ q: 'tec', sector_id: undefined, pagina: 2, tam: '' })).toBe('?q=tec&pagina=2')
    expect(armarConsulta({})).toBe('')
  })
})
