// Datos de ejemplo con la forma exacta del contrato, para las pruebas de reportes.
import type { Colonia, GeoResultado, ReporteCercano, ReporteMio, TipoDano } from '../api/tipos.ts'

export const TIPOS_DANO: TipoDano[] = [
  { id: 1, codigo: 'bache', nombre: 'Bache' },
  { id: 2, codigo: 'hundimiento', nombre: 'Hundimiento' },
  { id: 3, codigo: 'grieta', nombre: 'Grieta' },
  { id: 4, codigo: 'alcantarilla_sin_tapa', nombre: 'Alcantarilla sin tapa' },
]

export const COLONIAS: Colonia[] = [
  { id: 12, nombre: 'Partido Escobedo', sector: { id: 1, nombre: 'Norte' }, activa: true, lat: 31.74, lon: -106.43 },
  { id: 13, nombre: 'Centro', sector: { id: 2, nombre: 'Centro' }, activa: true, lat: 31.74, lon: -106.48 },
]

export const GEO_TECNOLOGICO: GeoResultado = {
  etiqueta: 'Av. Tecnológico 1340, Partido Escobedo, Ciudad Juárez',
  lat: 31.7001,
  lon: -106.4302,
  calle: 'Av. Tecnológico',
  colonia_id: 12,
  colonia_nombre: 'Partido Escobedo',
  dentro_del_municipio: true,
}

export const GEO_SIN_COLONIA: GeoResultado = {
  etiqueta: 'Calle Sin Colonia 5, Ciudad Juárez',
  lat: 31.71,
  lon: -106.44,
  calle: 'Calle Sin Colonia',
  colonia_id: null,
  colonia_nombre: null,
  dentro_del_municipio: true,
}

// ReporteMio de un bache recién creado (como lo responde POST /api/reportes/baches)
export function reporteMio(parcial: Partial<ReporteMio> = {}): ReporteMio {
  return {
    id: 345,
    folio: 'BCH-2026-000123',
    categoria: 'bache',
    tipo_dano: { codigo: 'bache', nombre: 'Bache' },
    calle: 'Av. Tecnológico',
    colonia: { id: 12, nombre: 'Partido Escobedo' },
    lat: 31.7001,
    lon: -106.4302,
    descripcion: '',
    severidad: 'alta',
    tamano: 'grande',
    profundidad: 'media',
    carril: 'derecho',
    senalizado: null,
    nivel_agua: null,
    hay_riesgo: null,
    estado: 'recibido',
    sin_validar: true,
    confirmaciones: 0,
    creado_en: '2026-11-24T21:05:00Z', // 14:05 en Ciudad Juárez
    vigente_hasta: null,
    fecha_reparacion: null,
    antiguedad_dias: 0,
    puede_editar: true,
    motivo_rechazo: null,
    ...parcial,
  }
}

export function reporteCercano(parcial: Partial<ReporteCercano> = {}): ReporteCercano {
  const { puede_editar: _a, motivo_rechazo: _b, ...publico } = reporteMio()
  return { ...publico, id: 77, folio: 'BCH-2026-000050', confirmaciones: 2, antiguedad_dias: 3, distancia_m: 12, ...parcial }
}

// Un encharcamiento activo (como lo responde POST /api/reportes/encharcamientos). El contrato no dice qué trae `tipo_dano`
// en un encharcamiento; la interfaz no lo usa para esta categoría.
export function encharcamientoMio(parcial: Partial<ReporteMio> = {}): ReporteMio {
  return reporteMio({
    id: 500,
    folio: 'ENC-2026-000045',
    categoria: 'encharcamiento',
    tipo_dano: { codigo: 'encharcamiento', nombre: 'Encharcamiento' } as unknown as ReporteMio['tipo_dano'],
    severidad: null,
    tamano: null,
    profundidad: null,
    carril: null,
    nivel_agua: 'media_llanta',
    hay_riesgo: null,
    estado: 'activo',
    sin_validar: false,
    vigente_hasta: '2026-11-25T03:05:00Z', // 6 horas después: 20:05 en Ciudad Juárez
    puede_editar: false,
    ...parcial,
  })
}
