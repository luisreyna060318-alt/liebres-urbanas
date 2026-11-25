// Endpoints de reportes (sección 6 del contrato). Solo habla con la API: las reglas y los mensajes viven en otros archivos.
import { api, armarConsulta } from './cliente.ts'
import type {
  Categoria,
  NuevaConfirmacion,
  NuevoBache,
  NuevoEncharcamiento,
  Paginacion,
  ReporteCercano,
  ReporteDetalle,
  ReporteMio,
  ReportePublico,
  TipoConfirmacion,
} from './tipos.ts'

// Lo que se puede cambiar de un reporte propio: los mismos campos del alta, sin `forzar` (sección 6.6)
export type EdicionReporte = Omit<NuevoBache, 'forzar'> | Omit<NuevoEncharcamiento, 'forzar'>

// POST /api/reportes/baches (201). Si hay un bache abierto a 30 m o menos responde 409 POSIBLE_DUPLICADO
// (con `duplicados` en el ErrorApi) salvo que se mande forzar: true.
export function crearBache(datos: NuevoBache): Promise<ReporteMio> {
  return api.post<ReporteMio>('/api/reportes/baches', datos)
}

// POST /api/reportes/encharcamientos (201): se publica como Activo de inmediato
export function crearEncharcamiento(datos: NuevoEncharcamiento): Promise<ReporteMio> {
  return api.post<ReporteMio>('/api/reportes/encharcamientos', datos)
}

// GET /api/reportes/cercanos?categoria=&lat=&lon=  ->  ordenados por distancia (radio de 30 m o 50 m según la categoría)
export function pedirCercanos(categoria: Categoria, lat: number, lon: number): Promise<ReporteCercano[]> {
  return api.get<ReporteCercano[]>(`/api/reportes/cercanos${armarConsulta({ categoria, lat, lon })}`)
}

// POST /api/reportes/{id}/confirmaciones (201)  ->  el reporte actualizado, sin crear folio nuevo
export function confirmarReporte(id: number, tipo: TipoConfirmacion): Promise<ReportePublico> {
  const cuerpo: NuevaConfirmacion = { tipo }
  return api.post<ReportePublico>(`/api/reportes/${id}/confirmaciones`, cuerpo)
}

// GET /api/mis-reportes?pagina=1  ->  10 por página, del más reciente al más antiguo
export function pedirMisReportes(pagina: number): Promise<Paginacion<ReporteMio>> {
  return api.get<Paginacion<ReporteMio>>(`/api/mis-reportes${armarConsulta({ pagina })}`)
}

// GET /api/reportes/{id}  ->  ReporteDetalle (lo construye Carlos). Aquí sirve para precargar el formulario de edición.
export function pedirDetalle(id: number): Promise<ReporteDetalle> {
  return api.get<ReporteDetalle>(`/api/reportes/${id}`)
}

// PUT /api/reportes/{id}: 409 REPORTE_NO_EDITABLE si el reporte ya no está en Recibido
export function editarReporte(id: number, datos: EdicionReporte): Promise<ReporteMio> {
  return api.put<ReporteMio>(`/api/reportes/${id}`, datos)
}

// DELETE /api/reportes/{id} (204): también 409 REPORTE_NO_EDITABLE
export function borrarReporte(id: number): Promise<void> {
  return api.delete<void>(`/api/reportes/${id}`)
}
