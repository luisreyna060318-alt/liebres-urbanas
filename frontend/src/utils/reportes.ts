// Datos y validaciones de los formularios de reporte. Dan respuesta inmediata en el cliente con las mismas reglas
// del servidor (contrato, secciones 6.2 y 6.3); el servidor vuelve a validar todo.
// Los errores se indexan con el nombre del campo de la API, así se mezclan con los `campos` que devuelva el servidor.
import type {
  Carril,
  NivelAgua,
  NuevoBache,
  NuevoEncharcamiento,
  Profundidad,
  ReportePublico,
  Tamano,
  TipoDanoCodigo,
} from '../api/tipos.ts'

export type Errores = Record<string, string>

// --- Ubicación: lo que captura SelectorUbicacion ---
// Todo es texto porque así viene de los campos; se convierte a número hasta armar la petición.
export interface DatosUbicacion {
  calle: string
  colonia_id: string // id de la colonia como texto ("" = sin elegir)
  lat: string
  lon: string
}

export const UBICACION_VACIA: DatosUbicacion = { calle: '', colonia_id: '', lat: '', lon: '' }

// Acepta "31.7001" y también "31,7001" (así se escribe en español). Devuelve NaN si no es un número.
export function numeroDe(texto: string): number {
  const limpio = texto.trim().replace(',', '.')
  return limpio === '' ? Number.NaN : Number(limpio)
}

function validarCoordenada(texto: string, nombre: 'latitud' | 'longitud', limite: number): string {
  if (!texto.trim()) return `Falta la ${nombre}. Busca una dirección, usa tu ubicación o captúrala a mano.`
  const numero = numeroDe(texto)
  if (Number.isNaN(numero) || Math.abs(numero) > limite) {
    return `La ${nombre} debe ser un número entre -${limite} y ${limite}.`
  }
  return ''
}

export function validarUbicacion(u: DatosUbicacion): Errores {
  const errores: Errores = {}
  if (!u.calle.trim()) errores.calle = 'Escribe la calle.'
  if (!u.colonia_id) errores.colonia_id = 'Elige la colonia.'
  const lat = validarCoordenada(u.lat, 'latitud', 90)
  if (lat) errores.lat = lat
  const lon = validarCoordenada(u.lon, 'longitud', 180)
  if (lon) errores.lon = lon
  return errores
}

// La descripción es opcional; el límite (500) llega de GET /api/reglas
export function validarDescripcion(texto: string, maximo: number): string {
  if (texto.trim().length > maximo) return `La descripción no puede pasar de ${maximo} caracteres.`
  return ''
}

// --- Bache (HU-02.2): qué campos pide cada tipo de daño ---
export type CampoDano = 'tamano' | 'profundidad' | 'carril' | 'senalizado'

const CAMPOS_POR_TIPO: Record<TipoDanoCodigo, readonly CampoDano[]> = {
  bache: ['tamano', 'profundidad', 'carril'],
  hundimiento: ['tamano', 'carril'],
  grieta: ['tamano', 'carril'],
  alcantarilla_sin_tapa: ['senalizado'], // su severidad es Alta automática: la pone el servidor
}

export function camposDeTipo(codigo: string): readonly CampoDano[] {
  return CAMPOS_POR_TIPO[codigo as TipoDanoCodigo] ?? []
}

export interface DatosBache {
  tipo_dano_codigo: TipoDanoCodigo | ''
  tamano: Tamano | ''
  profundidad: Profundidad | ''
  carril: Carril | ''
  senalizado: 'si' | 'no' | '' // "" = sin responder
  descripcion: string
}

export const BACHE_VACIO: DatosBache = {
  tipo_dano_codigo: '',
  tamano: '',
  profundidad: '',
  carril: '',
  senalizado: '',
  descripcion: '',
}

const MENSAJE_CAMPO: Record<CampoDano, string> = {
  tamano: 'Elige el tamaño del daño.',
  profundidad: 'Elige la profundidad.',
  carril: 'Elige el carril afectado.',
  senalizado: 'Indica si el punto está señalizado.',
}

// Solo se exigen los campos del tipo elegido; los demás se ignoran aunque tengan algo capturado
export function validarBache(u: DatosUbicacion, d: DatosBache, descripcionMax: number): Errores {
  const errores: Errores = { ...validarUbicacion(u) }
  if (!d.tipo_dano_codigo) errores.tipo_dano_codigo = 'Elige el tipo de daño.'
  for (const campo of camposDeTipo(d.tipo_dano_codigo)) {
    if (!d[campo]) errores[campo] = MENSAJE_CAMPO[campo]
  }
  const descripcion = validarDescripcion(d.descripcion, descripcionMax)
  if (descripcion) errores.descripcion = descripcion
  return errores
}

// Campos de un bache que se pueden enviar al crear (POST) o al editar (PUT). Los que no aplican al tipo van en null
// (como en el contrato). Se asume que validarBache ya pasó sin errores.
export function armarCamposBache(u: DatosUbicacion, d: DatosBache): Omit<NuevoBache, 'forzar'> {
  const campos = camposDeTipo(d.tipo_dano_codigo)
  return {
    tipo_dano_codigo: d.tipo_dano_codigo as TipoDanoCodigo,
    lat: numeroDe(u.lat),
    lon: numeroDe(u.lon),
    calle: u.calle.trim(),
    colonia_id: Number(u.colonia_id),
    descripcion: d.descripcion.trim(),
    tamano: campos.includes('tamano') ? (d.tamano as Tamano) : null,
    profundidad: campos.includes('profundidad') ? (d.profundidad as Profundidad) : null,
    carril: campos.includes('carril') ? (d.carril as Carril) : null,
    senalizado: campos.includes('senalizado') ? d.senalizado === 'si' : null,
  }
}

// Cuerpo de POST /api/reportes/baches: los campos más `forzar` (true = "reportarlo de todos modos")
export function armarBache(u: DatosUbicacion, d: DatosBache, forzar = false): NuevoBache {
  return { ...armarCamposBache(u, d), forzar }
}

// Los datos de un reporte existente convertidos a lo que captura el formulario (para editarlo)
export function ubicacionDeReporte(r: ReportePublico): DatosUbicacion {
  return { calle: r.calle, colonia_id: String(r.colonia.id), lat: String(r.lat), lon: String(r.lon) }
}

export function bacheDeReporte(r: ReportePublico): DatosBache {
  return {
    tipo_dano_codigo: r.tipo_dano?.codigo ?? 'bache',
    tamano: r.tamano ?? '',
    profundidad: r.profundidad ?? '',
    carril: r.carril ?? '',
    senalizado: r.senalizado === null ? '' : r.senalizado ? 'si' : 'no',
    descripcion: r.descripcion,
  }
}

// --- Encharcamiento (HU-03.1) ---
export interface DatosEncharcamiento {
  nivel_agua: NivelAgua | ''
  hay_riesgo: 'si' | 'no' | '' // solo se pregunta cuando el nivel es "intransitable"
  descripcion: string
}

export const ENCHARCAMIENTO_VACIO: DatosEncharcamiento = { nivel_agua: '', hay_riesgo: '', descripcion: '' }

// "Intransitable" obliga a responder si hay vehículos varados o personas en riesgo (HU-03.1 CA3)
export function preguntaRiesgoVisible(d: DatosEncharcamiento): boolean {
  return d.nivel_agua === 'intransitable'
}

export function validarEncharcamiento(u: DatosUbicacion, d: DatosEncharcamiento, descripcionMax: number): Errores {
  const errores: Errores = { ...validarUbicacion(u) }
  if (!d.nivel_agua) errores.nivel_agua = 'Elige qué tan alta está el agua.'
  if (preguntaRiesgoVisible(d) && !d.hay_riesgo) {
    errores.hay_riesgo = 'Responde si hay vehículos varados o personas en riesgo.'
  }
  const descripcion = validarDescripcion(d.descripcion, descripcionMax)
  if (descripcion) errores.descripcion = descripcion
  return errores
}

// Cuerpo de POST /api/reportes/encharcamientos. `hay_riesgo` solo viaja con "intransitable"; en los demás niveles va en null.
export function armarEncharcamiento(u: DatosUbicacion, d: DatosEncharcamiento, forzar = false): NuevoEncharcamiento {
  return {
    lat: numeroDe(u.lat),
    lon: numeroDe(u.lon),
    calle: u.calle.trim(),
    colonia_id: Number(u.colonia_id),
    descripcion: d.descripcion.trim(),
    nivel_agua: d.nivel_agua as NivelAgua,
    hay_riesgo: preguntaRiesgoVisible(d) ? d.hay_riesgo === 'si' : null,
    forzar,
  }
}
