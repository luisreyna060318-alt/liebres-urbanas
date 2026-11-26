// Formulario para crear o editar una colonia (HU-06.1). Con `colonia` edita; sin ella, crea.
// Valida lo básico en el cliente; el servidor vuelve a validar todo (coordenadas dentro de Juárez, nombre repetido...)
// y sus mensajes por campo se muestran junto a cada campo.
import { useState } from 'react'
import { actualizarColonia, crearColonia } from '../api/catalogos.ts'
import { ErrorApi } from '../api/cliente.ts'
import type { Colonia, Sector } from '../api/tipos.ts'
import Alerta from './Alerta.tsx'
import Boton from './Boton.tsx'
import Campo from './Campo.tsx'
import CampoCasilla from './CampoCasilla.tsx'

export const NOMBRE_COLONIA_MIN = 2
export const NOMBRE_COLONIA_MAX = 120

interface Props {
  colonia: Colonia | null
  sectores: Sector[]
  alGuardar: (colonia: Colonia, eraNueva: boolean) => void
  alCancelar: () => void
}

// Texto -> número. '' es "sin valor" (null); un texto que no es número devuelve NaN
function leerNumero(texto: string): number | null {
  const limpio = texto.trim().replace(',', '.')
  return limpio === '' ? null : Number(limpio)
}

export default function FormularioColonia({ colonia, sectores, alGuardar, alCancelar }: Props) {
  const [nombre, setNombre] = useState(colonia?.nombre ?? '')
  const [sectorId, setSectorId] = useState(colonia ? String(colonia.sector.id) : '')
  const [lat, setLat] = useState(colonia?.lat != null ? String(colonia.lat) : '')
  const [lon, setLon] = useState(colonia?.lon != null ? String(colonia.lon) : '')
  const [activa, setActiva] = useState(colonia?.activa ?? true)
  const [errores, setErrores] = useState<Record<string, string>>({})
  const [errorGeneral, setErrorGeneral] = useState('')
  const [enviando, setEnviando] = useState(false)

  function validar(): Record<string, string> {
    const campos: Record<string, string> = {}
    const limpio = nombre.trim()
    if (limpio.length < NOMBRE_COLONIA_MIN) campos.nombre = `El nombre debe tener al menos ${NOMBRE_COLONIA_MIN} caracteres.`
    else if (limpio.length > NOMBRE_COLONIA_MAX) campos.nombre = `El nombre no puede pasar de ${NOMBRE_COLONIA_MAX} caracteres.`
    if (!sectorId) campos.sector_id = 'Elige un sector.'
    const latitud = leerNumero(lat)
    const longitud = leerNumero(lon)
    if (Number.isNaN(latitud)) campos.lat = 'La latitud debe ser un número, por ejemplo 31.7302.'
    if (Number.isNaN(longitud)) campos.lon = 'La longitud debe ser un número, por ejemplo -106.4801.'
    if ((latitud === null) !== (longitud === null) && !campos.lat && !campos.lon) {
      campos[latitud === null ? 'lat' : 'lon'] = 'Captura latitud y longitud juntas, o deja las dos vacías.'
    }
    return campos
  }

  async function enviar(e: React.SyntheticEvent) {
    e.preventDefault()
    setErrorGeneral('')
    const campos = validar()
    setErrores(campos)
    if (Object.keys(campos).length > 0) return

    const datos = { nombre: nombre.trim(), sector_id: Number(sectorId), lat: leerNumero(lat), lon: leerNumero(lon) }
    setEnviando(true)
    try {
      const guardada = colonia
        ? await actualizarColonia(colonia.id, { ...datos, activa })
        : await crearColonia(datos)
      alGuardar(guardada, colonia === null)
    } catch (error) {
      if (error instanceof ErrorApi && Object.keys(error.campos).length > 0) {
        setErrores(error.campos) // los datos capturados se conservan
        setErrorGeneral('Revisa los campos marcados.')
      } else {
        setErrorGeneral(error instanceof Error ? error.message : 'No se pudo guardar la colonia.')
      }
    } finally {
      setEnviando(false)
    }
  }

  const opcionesSector = sectores.map((s) => ({ valor: String(s.id), etiqueta: s.nombre }))

  return (
    <form className="formulario formulario-admin" onSubmit={(e) => void enviar(e)} noValidate aria-label={colonia ? `Editar ${colonia.nombre}` : 'Nueva colonia'}>
      <h2>{colonia ? `Editar ${colonia.nombre}` : 'Nueva colonia'}</h2>
      <Campo id="colonia-nombre" etiqueta="Nombre" valor={nombre} onCambio={setNombre} error={errores.nombre} maxLength={NOMBRE_COLONIA_MAX} requerido />
      <Campo
        id="colonia-sector"
        etiqueta="Sector"
        tipo="select"
        valor={sectorId}
        onCambio={setSectorId}
        opciones={opcionesSector}
        textoOpcionVacia="Elige un sector…"
        error={errores.sector_id}
        requerido
      />
      <Campo
        id="colonia-lat"
        etiqueta="Latitud"
        valor={lat}
        onCambio={setLat}
        modoEntrada="decimal"
        error={errores.lat}
        ayuda="Opcional. Debe estar dentro de Ciudad Juárez."
      />
      <Campo id="colonia-lon" etiqueta="Longitud" valor={lon} onCambio={setLon} modoEntrada="decimal" error={errores.lon} />
      {colonia && (
        <CampoCasilla
          id="colonia-activa"
          etiqueta="Activa (se ofrece en los formularios de reporte)"
          marcada={activa}
          onCambio={setActiva}
        />
      )}
      {errorGeneral && <Alerta tipo="error">{errorGeneral}</Alerta>}
      <div className="formulario-admin-botones">
        <Boton type="submit" cargando={enviando} textoCargando="Guardando…">
          {colonia ? 'Guardar cambios' : 'Crear colonia'}
        </Boton>
        <Boton variante="secundario" onClick={alCancelar} disabled={enviando}>
          Cancelar
        </Boton>
      </div>
    </form>
  )
}
