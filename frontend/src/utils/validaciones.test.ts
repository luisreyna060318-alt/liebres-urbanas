import { describe, expect, it } from 'vitest'
import {
  validarAceptaPrivacidad,
  validarCorreo,
  validarNombre,
  validarPassword,
  validarPasswordLogin,
} from './validaciones.ts'

describe('validarNombre', () => {
  it('pide un nombre de 2 a 80 caracteres', () => {
    expect(validarNombre('')).toMatch(/Escribe tu nombre/)
    expect(validarNombre('   ')).toMatch(/Escribe tu nombre/)
    expect(validarNombre('A')).toMatch(/al menos 2/)
    expect(validarNombre('x'.repeat(81))).toMatch(/80/)
    expect(validarNombre('Ana')).toBe('')
    expect(validarNombre('x'.repeat(80))).toBe('')
  })
})

describe('validarCorreo', () => {
  it('rechaza correos vacíos o mal formados y acepta uno válido', () => {
    expect(validarCorreo('')).not.toBe('')
    expect(validarCorreo('ana')).toMatch(/correo válido/)
    expect(validarCorreo('ana@ejemplo')).toMatch(/correo válido/)
    expect(validarCorreo('ana @ejemplo.com')).toMatch(/correo válido/)
    expect(validarCorreo('  ana@ejemplo.com  ')).toBe('')
  })
})

describe('validarPassword', () => {
  it('exige 8 caracteres o más, con letras y números', () => {
    expect(validarPassword('')).toMatch(/Escribe una contraseña/)
    expect(validarPassword('abc123')).toMatch(/al menos 8/)
    expect(validarPassword('abcdefgh')).toMatch(/letras y números/)
    expect(validarPassword('12345678')).toMatch(/letras y números/)
    expect(validarPassword('abcd1234')).toBe('')
  })

  it('usa el mínimo que manda el servidor', () => {
    expect(validarPassword('abcd1234', 10)).toMatch(/al menos 10/)
    expect(validarPassword('abcdefgh12', 10)).toBe('')
  })
})

describe('otras validaciones', () => {
  it('el login solo exige una contraseña escrita', () => {
    expect(validarPasswordLogin('')).not.toBe('')
    expect(validarPasswordLogin('x')).toBe('')
  })

  it('el registro exige aceptar el aviso de privacidad', () => {
    expect(validarAceptaPrivacidad(false)).toMatch(/aviso de privacidad/)
    expect(validarAceptaPrivacidad(true)).toBe('')
  })
})
