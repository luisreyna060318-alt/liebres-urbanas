// /zona (pública, HU-04.3): "¿Cómo está mi zona?". La persona escribe una dirección y pulsa Buscar (nunca se busca
// mientras escribe: Nominatim limita las consultas) o usa su ubicación, y ve los reportes activos a 1 km.
import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ErrorApi } from '../api/cliente.ts'
import { buscarDireccion } from '../api/geo.ts'
import type { GeoResultado } from '../api/tipos.ts'
import { pedirZona } from '../api/zona.ts'
import Alerta from '../componentes/Alerta.tsx'
import Boton from '../componentes/Boton.tsx'
import Campo from '../componentes/Campo.tsx'
import Estado from '../componentes/Estado.tsx'
import TarjetaReporte from '../componentes/TarjetaReporte.tsx'
import { useApi } from '../hooks/useApi.ts'
import { useTitulo } from '../hooks/useTitulo.ts'

// El punto que se consulta: viene de una dirección elegida o de la ubicación del dispositivo
interface Punto {
  lat: number
  lon: number
  etiqueta: string
}

interface Aviso {
  tipo: 'aviso' | 'error'
  texto: string
  reintento?: 'otra' | 'misma' // "otra": escribir otra dirección; "misma": repetir la búsqueda (falló el servicio)
}

const ID_DIRECCION = 'zona-direccion'

// Texto cuando el servidor dice que el punto (por ejemplo el del dispositivo) no está en Ciudad Juárez
const TEXTO_FUERA_DEL_MUNICIPIO = 'Ese punto está fuera de Ciudad Juárez; escribe una dirección de la ciudad.'

// 1000 -> "1 km"; 500 -> "500 m"
function textoRadio(metros: number): string {
  return metros >= 1000 ? `${metros / 1000} km` : `${metros} m`
}

export default function Zona() {
  useTitulo('¿Cómo está mi zona?')

  const [consulta, setConsulta] = useState('')
  const [buscando, setBuscando] = useState(false)
  const [ubicando, setUbicando] = useState(false)
  const [opciones, setOpciones] = useState<GeoResultado[]>([]) // varias direcciones: la persona elige
  const [aviso, setAviso] = useState<Aviso | null>(null)
  const [punto, setPunto] = useState<Punto | null>(null)
  // Número de la última búsqueda: si llega la respuesta de una anterior (Enter dos veces seguidas, por ejemplo) se descarta
  const ultimaBusqueda = useRef(0)

  function elegir(r: GeoResultado) {
    setOpciones([])
    if (!r.dentro_del_municipio) {
      setPunto(null)
      setAviso({ tipo: 'aviso', texto: 'Esa dirección está fuera de Ciudad Juárez. Solo tenemos reportes del municipio.', reintento: 'otra' })
      return
    }
    setAviso(null)
    setPunto({ lat: r.lat, lon: r.lon, etiqueta: r.etiqueta })
  }

  async function buscar() {
    const texto = consulta.trim()
    if (texto.length < 3) {
      setAviso({ tipo: 'aviso', texto: 'Escribe una dirección (calle y número, por ejemplo) y pulsa Buscar.' })
      return
    }
    const numero = ++ultimaBusqueda.current
    setBuscando(true)
    setAviso(null)
    setOpciones([])
    setPunto(null)
    try {
      const { resultados } = await buscarDireccion(texto)
      if (numero !== ultimaBusqueda.current) return // ya hay una búsqueda más nueva
      if (resultados.length === 0) {
        setAviso({ tipo: 'aviso', texto: 'No encontramos esa dirección. Revisa cómo la escribiste e inténtalo de nuevo.', reintento: 'otra' })
      } else if (resultados.length === 1) {
        elegir(resultados[0])
      } else {
        setOpciones(resultados)
      }
    } catch (e) {
      if (numero !== ultimaBusqueda.current) return
      if (e instanceof ErrorApi && e.codigo === 'SERVICIO_NO_DISPONIBLE') {
        setAviso({
          tipo: 'error',
          texto: 'El servicio de búsqueda de direcciones no está disponible por ahora. Inténtalo en unos minutos o usa tu ubicación.',
          reintento: 'misma',
        })
      } else {
        setAviso({ tipo: 'error', texto: e instanceof Error ? e.message : 'No se pudo buscar la dirección.', reintento: 'misma' })
      }
    } finally {
      if (numero === ultimaBusqueda.current) setBuscando(false)
    }
  }

  function usarMiUbicacion() {
    if (!('geolocation' in navigator) || !navigator.geolocation) {
      setAviso({ tipo: 'aviso', texto: 'Tu navegador no permite obtener la ubicación. Escribe una dirección y pulsa Buscar.' })
      return
    }
    ultimaBusqueda.current++ // una búsqueda de dirección que siga en camino ya no debe pisar este resultado
    setBuscando(false)
    setUbicando(true)
    setAviso(null)
    setOpciones([])
    navigator.geolocation.getCurrentPosition(
      (posicion) => {
        setUbicando(false)
        setPunto({ lat: posicion.coords.latitude, lon: posicion.coords.longitude, etiqueta: 'Tu ubicación' })
      },
      (falla) => {
        setUbicando(false)
        setPunto(null)
        setAviso({
          tipo: 'aviso',
          texto:
            falla.code === 1 // PERMISSION_DENIED
              ? 'No diste permiso para usar tu ubicación. Escribe una dirección y pulsa Buscar.'
              : 'No se pudo obtener tu ubicación. Escribe una dirección y pulsa Buscar.',
        })
      },
      { timeout: 10_000 },
    )
  }

  function alEnviar(evento: FormEvent) {
    evento.preventDefault() // Enter en el campo equivale a pulsar Buscar
    void buscar()
  }

  function intentarDeNuevo() {
    setAviso(null)
    document.getElementById(ID_DIRECCION)?.focus()
  }

  return (
    <section>
      <h1>¿Cómo está mi zona?</h1>
      <p>Escribe una dirección de Ciudad Juárez, o usa tu ubicación, para ver los baches y encharcamientos activos a 1 km.</p>

      <form className="zona-formulario" role="search" aria-label="Buscar una zona" onSubmit={alEnviar}>
        <Campo
          id={ID_DIRECCION}
          etiqueta="Dirección"
          valor={consulta}
          onCambio={setConsulta}
          autoComplete="off"
          ayuda="Escribe la calle y el número, y pulsa Buscar (o Enter)."
        />
        <div className="zona-botones">
          <Boton type="submit" cargando={buscando} textoCargando="Buscando…">
            Buscar
          </Boton>
          <Boton variante="secundario" onClick={usarMiUbicacion} cargando={ubicando} textoCargando="Obteniendo ubicación…">
            Usar mi ubicación
          </Boton>
        </div>
      </form>

      {aviso && (
        <div className="zona-avisos">
          <Alerta tipo={aviso.tipo}>{aviso.texto}</Alerta>
          {aviso.reintento === 'otra' && <Boton variante="secundario" onClick={intentarDeNuevo}>Intentar de nuevo</Boton>}
          {aviso.reintento === 'misma' && (
            <Boton variante="secundario" onClick={() => void buscar()}>
              Reintentar
            </Boton>
          )}
        </div>
      )}

      {opciones.length > 0 && (
        <div className="zona-elegir" role="group" aria-labelledby="zona-elegir-titulo">
          <p id="zona-elegir-titulo">
            <strong>Encontramos varias direcciones. Elige la correcta:</strong>
          </p>
          <ul className="resultados-ubicacion">
            {opciones.map((r) => (
              <li key={`${r.lat},${r.lon},${r.etiqueta}`}>
                <Boton variante="secundario" onClick={() => elegir(r)}>
                  <span className="solo-lectores">Elegir:</span> {r.etiqueta}
                </Boton>
              </li>
            ))}
          </ul>
        </div>
      )}

      {punto && <ReportesDeZona key={`${punto.lat},${punto.lon}`} punto={punto} />}
    </section>
  )
}

// Pide y muestra los reportes de un punto. Se monta solo cuando ya hay un punto elegido.
function ReportesDeZona({ punto }: { punto: Punto }) {
  // 422 FUERA_DEL_MUNICIPIO no es una falla que se arregle reintentando: se devuelve como resultado propio
  const zona = useApi(async () => {
    try {
      return await pedirZona(punto.lat, punto.lon)
    } catch (e) {
      if (e instanceof ErrorApi && e.codigo === 'FUERA_DEL_MUNICIPIO') return 'fuera' as const
      throw e
    }
  }, [punto.lat, punto.lon])

  if (zona.datos === 'fuera') {
    return (
      <div className="zona-avisos">
        <Alerta tipo="aviso">{TEXTO_FUERA_DEL_MUNICIPIO}</Alerta>
      </div>
    )
  }

  const items = zona.datos?.items ?? []
  const radio = zona.datos ? textoRadio(zona.datos.radio_m) : '' // el servidor informa el radio; solo se usa con datos

  return (
    <section aria-labelledby="zona-titulo">
      <h2 id="zona-titulo">Reportes activos cerca de: {punto.etiqueta}</h2>

      <Estado
        cargando={zona.cargando}
        error={zona.error}
        vacio={zona.datos?.total === 0}
        textoCargando="Buscando reportes en tu zona…"
        textoVacio={`No hay reportes activos a ${radio}.`}
        onReintentar={zona.recargar}
      >
        <p className="zona-resumen" role="status">
          {zona.datos?.total === 1 ? 'Hay 1 reporte activo' : `Hay ${zona.datos?.total} reportes activos`} a {radio}. Los encharcamientos
          intransitables aparecen primero; el resto, del más cercano al más lejano.
          {zona.datos && zona.datos.total > items.length && ` Mostrando los ${items.length} primeros.`}
        </p>
        <ul className="lista-reportes">
          {items.map((r) => {
            const intransitable = r.nivel_agua === 'intransitable'
            return (
              <li key={r.id} className={intransitable ? 'zona-intransitable' : undefined}>
                <TarjetaReporte
                  reporte={r}
                  acciones={
                    <Link to={`/reportes/${r.id}`} className="boton boton-secundario">
                      Ver detalle <span className="solo-lectores">de {r.folio}</span>
                    </Link>
                  }
                >
                  {intransitable && (
                    <p className="zona-leyenda-intransitable">
                      <span aria-hidden="true">⚠ </span>
                      Intransitable: evita pasar por aquí
                    </p>
                  )}
                </TarjetaReporte>
              </li>
            )
          })}
        </ul>
      </Estado>
    </section>
  )
}
