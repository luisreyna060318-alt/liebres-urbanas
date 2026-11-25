// Cliente de la API: un envoltorio de fetch que agrega el token, usa la URL base
// y convierte los errores HTTP en un ErrorApi con el mensaje del servidor.
import { borrarSesion, leerToken } from './sesion.ts'
import type { CuerpoError, ReporteCercano } from './tipos.ts'

// URL base de la API (se define en frontend/.env, ver .env.example)
const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const MENSAJE_SIN_RED = 'No se pudo conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.'

// Error de la API. Corresponde al cuerpo {detail, codigo, campos} del contrato (sección 1).
//   status: código HTTP (0 si ni siquiera hubo respuesta)
//   codigo: etiqueta estable, por ejemplo "CORREO_REGISTRADO"
//   detail: mensaje en español para mostrar a la persona (también es el `message` del Error)
//   campos: mensajes por campo en los 422, por ejemplo { password: "..." }
export class ErrorApi extends Error {
  status: number
  codigo: string
  detail: string
  campos: Record<string, string>
  duplicados: ReporteCercano[]

  constructor(
    status: number,
    codigo: string,
    detail: string,
    campos: Record<string, string> = {},
    duplicados: ReporteCercano[] = [],
  ) {
    super(detail)
    this.name = 'ErrorApi'
    this.status = status
    this.codigo = codigo
    this.detail = detail
    this.campos = campos
    this.duplicados = duplicados
  }
}

// --- Qué hacer cuando la sesión ya no sirve (401 NO_AUTENTICADO) ---
// AuthProvider registra aquí su función para cerrar la sesión; así este archivo no depende de React.
let alExpirarSesion: (() => void) | null = null

export function registrarAlExpirarSesion(funcion: (() => void) | null): void {
  alExpirarSesion = funcion
}

// Convierte el cuerpo del error en un ErrorApi. Si el servidor respondió algo fuera del contrato
// (por ejemplo, el 422 de FastAPI sin formato propio o un fallo del proxy) se muestra un mensaje genérico.
function leerError(status: number, cuerpo: unknown): ErrorApi {
  const datos = (cuerpo ?? {}) as Partial<CuerpoError> & { detail?: unknown }

  if (typeof datos.detail === 'string') {
    return new ErrorApi(status, String(datos.codigo ?? 'ERROR'), datos.detail, datos.campos ?? {}, datos.duplicados ?? [])
  }

  if (Array.isArray(datos.detail)) {
    // Respaldo: lista de errores de Pydantic [{loc, msg}] sin el formato del contrato
    const campos: Record<string, string> = {}
    for (const item of datos.detail as { loc?: unknown[]; msg?: string }[]) {
      const campo = String(item.loc?.[item.loc.length - 1] ?? 'general')
      campos[campo] = (item.msg ?? 'Dato no válido').replace(/^Value error, /, '')
    }
    const resumen = Object.values(campos).join('. ') || 'Revisa los datos capturados.'
    return new ErrorApi(status, 'VALIDACION', resumen, campos)
  }

  return new ErrorApi(status, 'ERROR', `El servidor respondió con un error (${status}). Inténtalo de nuevo.`)
}

// Arma "?a=1&b=2" sin los valores vacíos. Sirve para los filtros y la paginación de las demás pantallas.
export function armarConsulta(parametros: Record<string, string | number | boolean | null | undefined>): string {
  const consulta = new URLSearchParams()
  for (const [clave, valor] of Object.entries(parametros)) {
    if (valor === undefined || valor === null || valor === '') continue
    consulta.set(clave, String(valor))
  }
  const texto = consulta.toString()
  return texto ? `?${texto}` : ''
}

interface Opciones {
  metodo?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  cuerpo?: unknown // se envía como JSON
}

export async function peticion<T>(ruta: string, opciones: Opciones = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  const token = leerToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let body: string | undefined
  if (opciones.cuerpo !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opciones.cuerpo)
  }

  let respuesta: Response
  try {
    respuesta = await fetch(`${API_URL}${ruta}`, { method: opciones.metodo ?? 'GET', headers, body })
  } catch {
    // fetch solo falla así cuando no hay red o el servidor no responde
    throw new ErrorApi(0, 'SIN_CONEXION', MENSAJE_SIN_RED)
  }

  // 204 no trae cuerpo
  if (respuesta.status === 204) return undefined as T

  // Si el cuerpo no es JSON válido, se queda en null
  const cuerpo: unknown = await respuesta.json().catch(() => null)

  if (!respuesta.ok) {
    const error = leerError(respuesta.status, cuerpo)
    // Token faltante, vencido o inválido: se borra la sesión y se avisa a AuthProvider.
    // Un 401 CREDENCIALES (login fallido) no entra aquí: no hay sesión que cerrar.
    if (error.status === 401 && error.codigo === 'NO_AUTENTICADO') {
      borrarSesion()
      alExpirarSesion?.()
    }
    throw error
  }

  return cuerpo as T
}

// Atajos para los métodos más usados
export const api = {
  get: <T>(ruta: string) => peticion<T>(ruta),
  post: <T>(ruta: string, cuerpo?: unknown) => peticion<T>(ruta, { metodo: 'POST', cuerpo }),
  put: <T>(ruta: string, cuerpo?: unknown) => peticion<T>(ruta, { metodo: 'PUT', cuerpo }),
  delete: <T>(ruta: string) => peticion<T>(ruta, { metodo: 'DELETE' }),
}
