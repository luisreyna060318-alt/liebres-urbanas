// Se ejecuta antes de cada archivo de pruebas.
// Agrega los verificadores de DOM (toBeInTheDocument, toHaveAttribute...) y limpia lo que cada prueba dejó.
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'
import { olvidarReglas } from '../api/reglas.ts'
import { borrarSesion } from '../api/sesion.ts'

afterEach(() => {
  cleanup()
  borrarSesion()
  olvidarReglas()
  vi.useRealTimers()
  vi.unstubAllGlobals()
  Reflect.deleteProperty(navigator, 'geolocation') // lo define simularGeolocalizacion
})
