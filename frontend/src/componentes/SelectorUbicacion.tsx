// Elige dónde está el daño (HU-02.1 CA1). Tres caminos, todos terminan en los mismos campos corregibles:
//   1) escribir una dirección y pulsar "Buscar" (o Enter): hasta 5 resultados para elegir,
//   2) "Usar mi ubicación" (geolocalización del navegador + GET /api/geo/inversa),
//   3) capturar calle, colonia y coordenadas a mano (también es la salida si el servicio de mapas no responde).
// No busca mientras se escribe: Nominatim limita las consultas. Es un componente controlado:
//   <SelectorUbicacion valor={ubicacion} onCambio={setUbicacion} errores={errores} />
// Los campos usan los ids campo-calle, campo-colonia_id, campo-lat y campo-lon para poder enfocarlos al validar.
import { useState } from 'react'
import { buscarDireccion, geocodificarInversa } from '../api/geo.ts'
import { ErrorApi } from '../api/cliente.ts'
import { pedirColonias } from '../api/catalogos.ts'
import type { GeoResultado } from '../api/tipos.ts'
import { useApi } from '../hooks/useApi.ts'
import type { DatosUbicacion, Errores } from '../utils/reportes.ts'
import Alerta from './Alerta.tsx'
import Boton from './Boton.tsx'
import Campo from './Campo.tsx'

interface Props {
  valor: DatosUbicacion
  onCambio: (valor: DatosUbicacion) => void
  errores?: Errores
}

type AvisoUbicacion = { tipo: 'aviso' | 'error' | 'info'; texto: string }

const MAX_RESULTADOS = 5

export default function SelectorUbicacion({ valor, onCambio, errores = {} }: Props) {
  const [consulta, setConsulta] = useState('')
  const [resultados, setResultados] = useState<GeoResultado[]>([])
  const [buscando, setBuscando] = useState(false)
  const [ubicando, setUbicando] = useState(false)
  const [aviso, setAviso] = useState<AvisoUbicacion | null>(null)
  const [manual, setManual] = useState(false) // true cuando la persona prefiere (o debe) capturar todo a mano

  // Solo colonias activas; con tam=500 llegan todas en una página para llenar la lista
  const colonias = useApi(() => pedirColonias({ tam: 500, solo_activas: true }))
  const opcionesColonia = [...(colonias.datos?.items ?? [])]
    .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'))
    .map((c) => ({ valor: String(c.id), etiqueta: `${c.nombre} (${c.sector.nombre})` }))

  // Los campos se muestran cuando ya hay algo que corregir, cuando se pide captura manual o si hay un error que señalar
  const hayDatos = Boolean(valor.calle || valor.colonia_id || valor.lat || valor.lon)
  const mostrarCampos = hayDatos || manual || Object.keys(errores).length > 0

  function cambiar(parcial: Partial<DatosUbicacion>) {
    onCambio({ ...valor, ...parcial })
  }

  // Copia un resultado de Nominatim a los campos y avisa si falta algo
  function aplicarResultado(r: GeoResultado, lista: { id: number }[] | undefined) {
    // Si el catálogo ya cargó y la colonia no está entre las activas, se deja vacía para que la persona elija
    const coloniaValida = r.colonia_id !== null && (!lista || lista.some((c) => c.id === r.colonia_id))
    onCambio({
      calle: r.calle,
      colonia_id: coloniaValida ? String(r.colonia_id) : '',
      lat: String(r.lat),
      lon: String(r.lon),
    })
    setResultados([])

    if (!r.dentro_del_municipio) {
      setAviso({
        tipo: 'aviso',
        texto: 'Esta ubicación parece estar fuera de Ciudad Juárez. Solo se registran reportes dentro del municipio.',
      })
    } else if (!coloniaValida) {
      setAviso({ tipo: 'info', texto: 'No reconocimos la colonia de esa dirección. Elígela de la lista.' })
    } else {
      setAviso({ tipo: 'info', texto: 'Ubicación elegida. Revisa la calle y la colonia; puedes corregirlas.' })
    }
  }

  // Cuando el servicio de mapas no responde, la persona no se queda bloqueada
  function avisarServicioCaido() {
    setManual(true)
    setAviso({
      tipo: 'aviso',
      texto:
        'El servicio de búsqueda de direcciones no está disponible por ahora. Escribe la calle, elige la colonia y captura las coordenadas a mano.',
    })
  }

  async function buscar() {
    const texto = consulta.trim()
    if (texto.length < 3) {
      setAviso({ tipo: 'aviso', texto: 'Escribe una dirección (calle y número, por ejemplo) y pulsa Buscar.' })
      return
    }
    setBuscando(true)
    setAviso(null)
    setResultados([])
    try {
      const respuesta = await buscarDireccion(texto)
      const encontrados = respuesta.resultados.slice(0, MAX_RESULTADOS)
      setResultados(encontrados)
      if (encontrados.length === 0) {
        setAviso({
          tipo: 'aviso',
          texto: 'No encontramos esa dirección. Revisa cómo la escribiste e inténtalo de nuevo, o usa tu ubicación.',
        })
      }
    } catch (e) {
      if (e instanceof ErrorApi && e.codigo === 'SERVICIO_NO_DISPONIBLE') {
        avisarServicioCaido()
      } else {
        setAviso({ tipo: 'error', texto: e instanceof Error ? e.message : 'No se pudo buscar la dirección.' })
      }
    } finally {
      setBuscando(false)
    }
  }

  function usarMiUbicacion() {
    if (!('geolocation' in navigator) || !navigator.geolocation) {
      setManual(true)
      setAviso({
        tipo: 'aviso',
        texto: 'Tu navegador no permite obtener la ubicación. Busca una dirección o captura la ubicación a mano.',
      })
      return
    }

    setUbicando(true)
    setAviso(null)
    navigator.geolocation.getCurrentPosition(
      async (posicion) => {
        const lat = Number(posicion.coords.latitude.toFixed(6))
        const lon = Number(posicion.coords.longitude.toFixed(6))
        try {
          aplicarResultado(await geocodificarInversa(lat, lon), colonias.datos?.items)
        } catch (e) {
          // Las coordenadas del dispositivo ya se conocen: se conservan y se pide el resto a mano
          cambiar({ lat: String(lat), lon: String(lon) })
          setManual(true)
          if (e instanceof ErrorApi && e.codigo === 'SERVICIO_NO_DISPONIBLE') {
            avisarServicioCaido()
          } else {
            setAviso({ tipo: 'error', texto: 'No se pudo obtener la dirección de tu ubicación. Escribe la calle y elige la colonia.' })
          }
        } finally {
          setUbicando(false)
        }
      },
      (falla) => {
        setUbicando(false)
        setManual(true)
        setAviso({
          tipo: 'aviso',
          texto:
            falla.code === 1 // PERMISSION_DENIED
              ? 'No diste permiso para usar tu ubicación. Busca una dirección o captura la ubicación a mano.'
              : 'No se pudo obtener tu ubicación. Busca una dirección o captura la ubicación a mano.',
        })
      },
      { enableHighAccuracy: true, timeout: 10_000 },
    )
  }

  return (
    <fieldset className="selector-ubicacion">
      <legend>Ubicación del daño</legend>

      <Campo
        id="campo-buscar"
        etiqueta="Dirección"
        valor={consulta}
        onCambio={setConsulta}
        alPresionarEnter={buscar}
        ayuda="Escribe la calle y el número, y pulsa Buscar (o Enter)."
      />

      <div className="selector-ubicacion-botones">
        <Boton onClick={buscar} cargando={buscando} textoCargando="Buscando…">
          Buscar
        </Boton>
        <Boton variante="secundario" onClick={usarMiUbicacion} cargando={ubicando} textoCargando="Obteniendo ubicación…">
          Usar mi ubicación
        </Boton>
      </div>

      {aviso && <Alerta tipo={aviso.tipo}>{aviso.texto}</Alerta>}

      {resultados.length > 0 && (
        <div role="group" aria-labelledby="resultados-titulo">
          <p id="resultados-titulo" className="selector-ubicacion-titulo">
            Elige la dirección correcta:
          </p>
          <ul className="resultados-ubicacion">
            {resultados.map((r) => (
              <li key={`${r.lat},${r.lon},${r.etiqueta}`}>
                <Boton variante="secundario" onClick={() => aplicarResultado(r, colonias.datos?.items)}>
                  <span className="solo-lectores">Elegir:</span> {r.etiqueta}
                </Boton>
              </li>
            ))}
          </ul>
        </div>
      )}

      {colonias.error && (
        <Alerta tipo="error">
          No se pudo cargar la lista de colonias. {colonias.error}{' '}
          <Boton variante="secundario" onClick={colonias.recargar}>
            Reintentar
          </Boton>
        </Alerta>
      )}

      {mostrarCampos ? (
        <div className="selector-ubicacion-campos">
          <Campo
            id="campo-calle"
            etiqueta="Calle"
            valor={valor.calle}
            onCambio={(calle) => cambiar({ calle })}
            error={errores.calle}
            autoComplete="off"
            requerido
          />
          <Campo
            id="campo-colonia_id"
            etiqueta="Colonia"
            tipo="select"
            textoOpcionVacia={colonias.cargando ? 'Cargando colonias…' : 'Elige la colonia…'}
            opciones={opcionesColonia}
            valor={valor.colonia_id}
            onCambio={(colonia_id) => cambiar({ colonia_id })}
            error={errores.colonia_id}
            requerido
          />
          <div className="selector-ubicacion-coordenadas">
            <Campo
              id="campo-lat"
              etiqueta="Latitud"
              modoEntrada="decimal"
              valor={valor.lat}
              onCambio={(lat) => cambiar({ lat })}
              ayuda="Ejemplo: 31.7001"
              error={errores.lat}
              requerido
            />
            <Campo
              id="campo-lon"
              etiqueta="Longitud"
              modoEntrada="decimal"
              valor={valor.lon}
              onCambio={(lon) => cambiar({ lon })}
              ayuda="Ejemplo: -106.4302"
              error={errores.lon}
              requerido
            />
          </div>
        </div>
      ) : (
        <p>
          <Boton variante="secundario" onClick={() => setManual(true)}>
            Capturar la ubicación a mano
          </Boton>
        </p>
      )}
    </fieldset>
  )
}
