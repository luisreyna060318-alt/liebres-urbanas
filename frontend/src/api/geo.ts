// Ubicación (sección 5 del contrato): el servidor consulta Nominatim; el navegador nunca llama a un servicio externo.
import { api, armarConsulta } from './cliente.ts'
import type { GeoBusqueda, GeoResultado } from './tipos.ts'

// GET /api/geo/buscar?q=...  ->  hasta 5 resultados ya restringidos a Ciudad Juárez (lista vacía si no hay coincidencias)
export function buscarDireccion(q: string): Promise<GeoBusqueda> {
  return api.get<GeoBusqueda>(`/api/geo/buscar${armarConsulta({ q })}`)
}

// GET /api/geo/inversa?lat=..&lon=..  ->  la dirección de unas coordenadas (por ejemplo las del dispositivo)
export function geocodificarInversa(lat: number, lon: number): Promise<GeoResultado> {
  return api.get<GeoResultado>(`/api/geo/inversa${armarConsulta({ lat, lon })}`)
}
