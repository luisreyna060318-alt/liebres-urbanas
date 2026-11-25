// GET /api/reglas: las cifras de negocio viven en el servidor (backend/app/core/reglas.py) y aquí solo se leen.
import { api } from './cliente.ts'
import type { Reglas } from './tipos.ts'

// Valores de respaldo (los mismos del diseño técnico) por si la API todavía no responde o falla.
// Así el formulario y el cierre por inactividad siempre tienen un número que usar.
export const REGLAS_RESPALDO: Reglas = {
  radio_duplicado_bache_m: 30,
  radio_duplicado_encharcamiento_m: 50,
  vigencia_encharcamiento_horas: 6,
  desmentidos_para_cerrar: 3,
  radio_zona_km: 1,
  max_reportes_por_hora: 10,
  descripcion_max: 500,
  password_min: 8,
  inactividad_min: 30,
  tam_pagina_consulta: 20,
  tam_pagina_mis_reportes: 10,
  umbral_lluvia_pct: 30,
  zona_horaria: 'America/Ciudad_Juarez',
}

export function pedirReglas(): Promise<Reglas> {
  return api.get<Reglas>('/api/reglas')
}

// Las reglas casi no cambian: se piden una vez por carga de la página y se comparten.
let pendiente: Promise<Reglas> | null = null

export function reglasCompartidas(): Promise<Reglas> {
  if (!pendiente) {
    pendiente = pedirReglas().catch((error: unknown) => {
      pendiente = null // si falló, la próxima vez se vuelve a intentar
      throw error
    })
  }
  return pendiente
}

// Solo para las pruebas: olvida lo que se guardó
export function olvidarReglas(): void {
  pendiente = null
}
