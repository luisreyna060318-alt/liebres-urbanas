// Textos en español para los valores del contrato (la API manda códigos como "media_llanta").
// Cada valor se muestra con palabras: nunca se deja solo un color o un ícono.
import type { Carril, Categoria, Estado, NivelAgua, Profundidad, Tamano } from '../api/tipos.ts'
import type { OpcionCampo } from '../componentes/Campo.tsx'

// Las leyendas del tamaño son las del requerimiento (HU-02.2)
export const ETIQUETA_TAMANO: Record<Tamano, string> = {
  chico: 'Chico: menos de 30 cm',
  mediano: 'Mediano: 30 cm a 1 m',
  grande: 'Grande: más de 1 m',
}

export const ETIQUETA_PROFUNDIDAD: Record<Profundidad, string> = {
  baja: 'Baja',
  media: 'Media',
  alta: 'Alta',
}

export const ETIQUETA_CARRIL: Record<Carril, string> = {
  orilla: 'Orilla de la calle',
  izquierdo: 'Carril izquierdo',
  derecho: 'Carril derecho',
  varios: 'Varios carriles',
}

export const ETIQUETA_NIVEL_AGUA: Record<NivelAgua, string> = {
  a_un_lado: 'A un lado de la calle',
  cubre_carril: 'Cubre un carril',
  media_llanta: 'A media llanta',
  intransitable: 'Intransitable',
}

export const ETIQUETA_ESTADO: Record<Estado, string> = {
  recibido: 'Recibido',
  validado: 'Validado',
  en_reparacion: 'En reparación',
  reparado: 'Reparado',
  rechazado: 'Rechazado',
  activo: 'Activo',
  historico: 'Histórico',
}

export const ETIQUETA_CATEGORIA: Record<Categoria, string> = {
  bache: 'Bache',
  encharcamiento: 'Encharcamiento',
}

// Ícono decorativo de cada categoría: siempre va junto al texto de ETIQUETA_CATEGORIA
export const ICONO_CATEGORIA: Record<Categoria, string> = {
  bache: '🚧',
  encharcamiento: '💧',
}

// Convierte uno de los diccionarios de arriba en las opciones de un <select>
export function opcionesDe(etiquetas: Record<string, string>): OpcionCampo[] {
  return Object.entries(etiquetas).map(([valor, etiqueta]) => ({ valor, etiqueta }))
}

// 0 -> "Reportado hoy", 1 -> "Hace 1 día", 5 -> "Hace 5 días" (RN-10: antigüedad en días)
export function textoAntiguedad(dias: number): string {
  if (dias <= 0) return 'Reportado hoy'
  return `Hace ${dias} ${dias === 1 ? 'día' : 'días'}`
}

// 12 -> "a 12 m"; 1250 -> "a 1.3 km"
export function textoDistancia(metros: number): string {
  if (metros < 1000) return `a ${Math.round(metros)} m`
  return `a ${(metros / 1000).toFixed(1)} km`
}
