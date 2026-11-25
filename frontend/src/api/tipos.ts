// Tipos y enumeraciones del contrato de la API (docs/plan/CONTRATO_API.md).
// Los nombres de campos y los valores se escriben igual que en el servidor: si el contrato cambia, cambia aquí.

// --- Enumeraciones (sección 2 del contrato) ---
export type Rol = 'ciudadano' | 'moderador' | 'coordinador'
export type Categoria = 'bache' | 'encharcamiento'
export type TipoDanoCodigo = 'bache' | 'hundimiento' | 'grieta' | 'alcantarilla_sin_tapa'
export type Tamano = 'chico' | 'mediano' | 'grande'
export type Profundidad = 'baja' | 'media' | 'alta'
export type Carril = 'orilla' | 'izquierdo' | 'derecho' | 'varios'
export type Severidad = 'baja' | 'media' | 'alta'
export type NivelAgua = 'a_un_lado' | 'cubre_carril' | 'media_llanta' | 'intransitable'
export type EstadoBache = 'recibido' | 'validado' | 'en_reparacion' | 'reparado' | 'rechazado'
export type EstadoEncharcamiento = 'activo' | 'historico' | 'rechazado'
export type Estado = EstadoBache | EstadoEncharcamiento
export type TipoConfirmacion = 'confirma' | 'sigue' | 'ya_no_hay'

// Listas con los valores permitidos, útiles para armar selects y validar
export const ROLES: readonly Rol[] = ['ciudadano', 'moderador', 'coordinador']
export const CATEGORIAS: readonly Categoria[] = ['bache', 'encharcamiento']

// --- Errores (sección 1) ---
export type CodigoError =
  | 'NO_AUTENTICADO'
  | 'CREDENCIALES'
  | 'SIN_PERMISO'
  | 'CUENTA_SUSPENDIDA'
  | 'ES_TU_REPORTE'
  | 'NO_ENCONTRADO'
  | 'CORREO_REGISTRADO'
  | 'POSIBLE_DUPLICADO'
  | 'YA_CONFIRMADO'
  | 'REPORTE_NO_EDITABLE'
  | 'TRANSICION_INVALIDA'
  | 'VALIDACION'
  | 'FUERA_DEL_MUNICIPIO'
  | 'LIMITE_HORARIO'
  | 'SERVICIO_NO_DISPONIBLE'

// Cuerpo de cualquier error que responde el servidor. `campos` solo viene en los 422 de validación;
// `duplicados` solo en el 409 POSIBLE_DUPLICADO.
export interface CuerpoError {
  detail: string
  codigo: CodigoError | string
  campos?: Record<string, string>
  duplicados?: ReporteCercano[]
}

// --- Cuenta y sesión (sección 3) ---
export interface UsuarioPublico {
  id: number
  nombre: string
  correo: string
  rol: Rol
}

export interface SesionRespuesta {
  access_token: string
  token_type: string
  expira_en_min: number
  usuario: UsuarioPublico
}

export interface DatosRegistro {
  nombre: string
  correo: string
  password: string
  acepta_privacidad: boolean
}

export interface DatosLogin {
  correo: string
  password: string
}

// --- Reglas y catálogos (sección 4) ---
export interface Reglas {
  radio_duplicado_bache_m: number
  radio_duplicado_encharcamiento_m: number
  vigencia_encharcamiento_horas: number
  desmentidos_para_cerrar: number
  radio_zona_km: number
  max_reportes_por_hora: number
  descripcion_max: number
  password_min: number
  inactividad_min: number
  tam_pagina_consulta: number
  tam_pagina_mis_reportes: number
  umbral_lluvia_pct: number
  zona_horaria: string
}

export interface Sector {
  id: number
  nombre: string
}

export interface Colonia {
  id: number
  nombre: string
  sector: Sector
  activa: boolean
  lat: number
  lon: number
}

export interface TipoDano {
  id: number
  codigo: TipoDanoCodigo
  nombre: string
}

export interface MotivoRechazo {
  id: number
  codigo: string
  nombre: string
  pide_explicacion: boolean
}

// --- Paginación (sección 1): ?pagina=1&tam=20 ---
export interface Paginacion<T> {
  items: T[]
  total: number
  pagina: number
  tam: number
}

// --- Ubicación (sección 5) ---
export interface GeoResultado {
  etiqueta: string
  lat: number
  lon: number
  calle: string
  colonia_id: number | null // null si el nombre no coincide con el catálogo: la persona elige la colonia
  colonia_nombre: string | null
  dentro_del_municipio: boolean
}

export interface GeoBusqueda {
  resultados: GeoResultado[]
}

// --- Reportes (sección 6) ---
// Lo que ve cualquier persona. Nunca incluye al autor.
export interface ReportePublico {
  id: number
  folio: string
  categoria: Categoria
  tipo_dano: { codigo: TipoDanoCodigo; nombre: string }
  calle: string
  colonia: { id: number; nombre: string }
  lat: number
  lon: number
  descripcion: string
  severidad: Severidad | null
  // Campos propios de bache (vienen en null si el reporte es un encharcamiento)
  tamano: Tamano | null
  profundidad: Profundidad | null
  carril: Carril | null
  senalizado: boolean | null
  // Campos propios de encharcamiento (null si es un bache)
  nivel_agua: NivelAgua | null
  hay_riesgo: boolean | null
  estado: Estado
  sin_validar: boolean
  confirmaciones: number
  creado_en: string // ISO 8601 UTC con Z
  vigente_hasta: string | null
  fecha_reparacion: string | null // solo fecha: "2026-11-20"
  antiguedad_dias: number
}

// ReportePublico + distancia: lo que devuelven /reportes/cercanos y el 409 POSIBLE_DUPLICADO
export interface ReporteCercano extends ReportePublico {
  distancia_m: number
}

export interface MotivoRechazoReporte {
  nombre: string
  texto: string | null
}

// Solo para el autor
export interface ReporteMio extends ReportePublico {
  puede_editar: boolean
  motivo_rechazo: MotivoRechazoReporte | null
}

// Del más reciente al más antiguo; no incluye quién hizo el cambio
export interface CambioEstado {
  estado_anterior: Estado | null
  estado_nuevo: Estado
  comentario: string | null
  creado_en: string
}

export interface ReporteDetalle extends ReportePublico {
  longevidad_dias: number
  ultima_actividad: string
  historial: CambioEstado[]
}

// Entradas para crear reportes (secciones 6.2 y 6.3)
export interface NuevoBache {
  tipo_dano_codigo: TipoDanoCodigo
  lat: number
  lon: number
  calle: string
  colonia_id: number
  descripcion?: string
  tamano?: Tamano | null
  profundidad?: Profundidad | null
  carril?: Carril | null
  senalizado?: boolean | null
  forzar?: boolean
}

export interface NuevoEncharcamiento {
  lat: number
  lon: number
  calle: string
  colonia_id: number
  descripcion?: string
  nivel_agua: NivelAgua
  hay_riesgo?: boolean | null
  forzar?: boolean
}

export interface NuevaConfirmacion {
  tipo: TipoConfirmacion
}
