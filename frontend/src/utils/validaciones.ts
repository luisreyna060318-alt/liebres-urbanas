// Validaciones en el cliente: dan respuesta inmediata, pero NO sustituyen a las del servidor.
// Cada función devuelve el mensaje de error, o '' si el valor es válido.
// Las reglas son las del contrato (sección 3): nombre de 2 a 80 caracteres, correo válido,
// contraseña de 8 o más caracteres con letras y números, y aviso de privacidad aceptado.

export const NOMBRE_MIN = 2
export const NOMBRE_MAX = 80
export const PASSWORD_MIN = 8 // respaldo: el valor real llega de GET /api/reglas (password_min)

export function validarNombre(valor: string): string {
  const nombre = valor.trim()
  if (!nombre) return 'Escribe tu nombre.'
  if (nombre.length < NOMBRE_MIN) return `El nombre debe tener al menos ${NOMBRE_MIN} caracteres.`
  if (nombre.length > NOMBRE_MAX) return `El nombre no puede pasar de ${NOMBRE_MAX} caracteres.`
  return ''
}

export function validarCorreo(valor: string): string {
  const correo = valor.trim()
  if (!correo) return 'Escribe tu correo electrónico.'
  if (correo.length > 254) return 'El correo es demasiado largo.'
  // Revisión sencilla: algo@algo.algo, sin espacios. El servidor hace la revisión completa.
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(correo)) return 'Escribe un correo válido, por ejemplo ana@ejemplo.com.'
  return ''
}

// Para crear cuenta: mínimo `minimo` caracteres (8), combinando letras y números
export function validarPassword(valor: string, minimo: number = PASSWORD_MIN): string {
  if (!valor) return 'Escribe una contraseña.'
  if (valor.length < minimo) return `La contraseña debe tener al menos ${minimo} caracteres.`
  if (!/\p{L}/u.test(valor) || !/\d/.test(valor)) return 'La contraseña debe combinar letras y números.'
  return ''
}

// Para iniciar sesión solo se exige que no esté vacía: el servidor decide si es correcta
export function validarPasswordLogin(valor: string): string {
  return valor ? '' : 'Escribe tu contraseña.'
}

export function validarAceptaPrivacidad(aceptada: boolean): string {
  return aceptada ? '' : 'Para crear tu cuenta debes aceptar el aviso de privacidad.'
}
