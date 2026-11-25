import { describe, expect, it } from 'vitest'
import { textoAntiguedad, textoDistancia } from './etiquetas.ts'
import { armarBache, BACHE_VACIO, camposDeTipo, numeroDe, validarBache, validarDescripcion, validarUbicacion } from './reportes.ts'
import type { DatosBache, DatosUbicacion } from './reportes.ts'

const UBICACION: DatosUbicacion = { calle: 'Av. Tecnológico', colonia_id: '12', lat: '31.7001', lon: '-106.4302' }

describe('campos por tipo de daño (HU-02.2)', () => {
  it('cada tipo pide solo sus campos', () => {
    expect(camposDeTipo('bache')).toEqual(['tamano', 'profundidad', 'carril'])
    expect(camposDeTipo('hundimiento')).toEqual(['tamano', 'carril'])
    expect(camposDeTipo('grieta')).toEqual(['tamano', 'carril'])
    expect(camposDeTipo('alcantarilla_sin_tapa')).toEqual(['senalizado'])
    expect(camposDeTipo('')).toEqual([])
  })
})

describe('validación de la ubicación', () => {
  it('pide calle, colonia y coordenadas', () => {
    const errores = validarUbicacion({ calle: ' ', colonia_id: '', lat: '', lon: '' })
    expect(Object.keys(errores).sort()).toEqual(['calle', 'colonia_id', 'lat', 'lon'])
  })

  it('acepta coma decimal y rechaza números fuera de rango o texto', () => {
    expect(numeroDe('31,7001')).toBe(31.7001)
    expect(validarUbicacion({ ...UBICACION, lat: '31,7001' })).toEqual({})
    expect(validarUbicacion({ ...UBICACION, lat: '120' }).lat).toMatch(/entre -90 y 90/)
    expect(validarUbicacion({ ...UBICACION, lon: 'abc' }).lon).toMatch(/entre -180 y 180/)
  })
})

describe('validación del bache', () => {
  const bache: DatosBache = { ...BACHE_VACIO, tipo_dano_codigo: 'bache', tamano: 'grande', profundidad: 'media', carril: 'derecho' }

  it('sin tipo de daño solo reclama el tipo', () => {
    expect(validarBache(UBICACION, BACHE_VACIO, 500)).toEqual({ tipo_dano_codigo: 'Elige el tipo de daño.' })
  })

  it('un bache exige tamaño, profundidad y carril', () => {
    const errores = validarBache(UBICACION, { ...BACHE_VACIO, tipo_dano_codigo: 'bache' }, 500)
    expect(Object.keys(errores).sort()).toEqual(['carril', 'profundidad', 'tamano'])
  })

  it('una grieta no exige profundidad y una alcantarilla exige señalizado', () => {
    const grieta: DatosBache = { ...BACHE_VACIO, tipo_dano_codigo: 'grieta', tamano: 'chico', carril: 'orilla' }
    expect(validarBache(UBICACION, grieta, 500)).toEqual({})
    const alcantarilla: DatosBache = { ...BACHE_VACIO, tipo_dano_codigo: 'alcantarilla_sin_tapa' }
    expect(validarBache(UBICACION, alcantarilla, 500)).toEqual({ senalizado: 'Indica si el punto está señalizado.' })
  })

  it('la descripción no puede pasar del límite que manda el servidor', () => {
    expect(validarDescripcion('a'.repeat(500), 500)).toBe('')
    expect(validarDescripcion('a'.repeat(501), 500)).toMatch(/500 caracteres/)
    expect(validarBache(UBICACION, { ...bache, descripcion: 'a'.repeat(501) }, 500).descripcion).toBeDefined()
  })

  it('armarBache usa los campos del contrato y deja en null los que no aplican', () => {
    expect(armarBache(UBICACION, { ...bache, descripcion: '  Hueco  ' })).toEqual({
      tipo_dano_codigo: 'bache',
      lat: 31.7001,
      lon: -106.4302,
      calle: 'Av. Tecnológico',
      colonia_id: 12,
      descripcion: 'Hueco',
      tamano: 'grande',
      profundidad: 'media',
      carril: 'derecho',
      senalizado: null,
      forzar: false,
    })
    const alcantarilla: DatosBache = { ...bache, tipo_dano_codigo: 'alcantarilla_sin_tapa', senalizado: 'no' }
    expect(armarBache(UBICACION, alcantarilla, true)).toMatchObject({
      tamano: null,
      profundidad: null,
      carril: null,
      senalizado: false,
      forzar: true,
    })
  })
})

describe('textos de antigüedad y distancia', () => {
  it('antigüedad en días', () => {
    expect(textoAntiguedad(0)).toBe('Reportado hoy')
    expect(textoAntiguedad(1)).toBe('Hace 1 día')
    expect(textoAntiguedad(5)).toBe('Hace 5 días')
  })

  it('distancia en metros o kilómetros', () => {
    expect(textoDistancia(12.4)).toBe('a 12 m')
    expect(textoDistancia(1250)).toBe('a 1.3 km')
  })
})
