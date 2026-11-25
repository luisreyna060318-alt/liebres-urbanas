// /tablero (solo coordinador, HU-07.1): indicadores con filtros de fecha y sector. Las cifras salen de la misma
// función de filtrado que la consulta pública, así coinciden con la lista (CA5). La ruta ya está protegida en App.tsx
// y el servidor vuelve a comprobar el rol.
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { pedirSectores } from '../api/catalogos.ts'
import { pedirTablero } from '../api/tablero.ts'
import type { Categoria, FiltroTablero, Tablero as DatosTablero } from '../api/tipos.ts'
import Boton from '../componentes/Boton.tsx'
import Campo from '../componentes/Campo.tsx'
import Estado from '../componentes/Estado.tsx'
import GraficaSemanal from '../componentes/GraficaSemanal.tsx'
import { useApi } from '../hooks/useApi.ts'
import { useTitulo } from '../hooks/useTitulo.ts'
import { ETIQUETA_CATEGORIA, ETIQUETA_ESTADO } from '../utils/etiquetas.ts'

interface Filtros {
  desde: string
  hasta: string
  sector_id: string
}
const SIN_FILTROS: Filtros = { desde: '', hasta: '', sector_id: '' }

function aFiltroApi(f: Filtros): FiltroTablero {
  return {
    desde: f.desde || undefined,
    hasta: f.hasta || undefined,
    sector_id: f.sector_id ? Number(f.sector_id) : undefined,
  }
}

const numero = (valor: number) => valor.toLocaleString('es-MX', { maximumFractionDigits: 1 })
const dias = (valor: number) => `${numero(valor)} ${valor === 1 ? 'día' : 'días'}`

export default function Tablero() {
  useTitulo('Tablero de indicadores')
  const [filtros, setFiltros] = useState<Filtros>(SIN_FILTROS)
  const clave = `${filtros.desde}|${filtros.hasta}|${filtros.sector_id}`
  const tablero = useApi(() => pedirTablero(aFiltroApi(filtros)), [clave])
  const datos = tablero.datos
  const vacio = datos !== null && datos.totales.total === 0 && datos.totales.rechazados === 0

  return (
    <section className="tablero">
      <h1>Tablero de indicadores</h1>
      <p>Cifras de baches y encharcamientos. Los filtros aplican a todos los indicadores.</p>

      <FormularioFiltros key={clave} inicial={filtros} onAplicar={setFiltros} onLimpiar={() => setFiltros(SIN_FILTROS)} />

      <Estado
        cargando={tablero.cargando}
        error={tablero.error}
        vacio={vacio}
        textoCargando="Cargando indicadores…"
        textoVacio="No hay reportes con estos filtros. Prueba con otro rango de fechas u otro sector."
        onReintentar={tablero.recargar}
      >
        {datos && <Indicadores datos={datos} />}
      </Estado>
    </section>
  )
}

function Indicadores({ datos }: { datos: DatosTablero }) {
  const { totales } = datos
  const categorias: Categoria[] = ['bache', 'encharcamiento']

  return (
    <>
      <h2>Totales</h2>
      <ul className="tablero-tarjetas">
        <li className="tablero-tarjeta">
          <span className="tablero-cifra">{totales.total}</span> reportes en total
        </li>
        <li className="tablero-tarjeta">
          <span className="tablero-cifra">{totales.bache}</span> baches
        </li>
        <li className="tablero-tarjeta">
          <span className="tablero-cifra">{totales.encharcamiento}</span> encharcamientos
        </li>
        <li className="tablero-tarjeta">
          <span className="tablero-cifra">{totales.rechazados}</span> rechazados (no suman en el total)
        </li>
        <li className="tablero-tarjeta">
          <span className="tablero-cifra">
            {datos.tiempo_promedio_reparacion_dias === null ? 'Sin datos' : dias(datos.tiempo_promedio_reparacion_dias)}
          </span>{' '}
          tiempo promedio de reparación (de Validado a Reparado
          {datos.reparados_medidos > 0 && `, ${datos.reparados_medidos} baches medidos`})
        </li>
      </ul>

      <div className="tablero-estados">
        {categorias.map((categoria) => (
          <div key={categoria}>
            <h3>{ETIQUETA_CATEGORIA[categoria]} por estado</h3>
            <dl className="tablero-lista-estados">
              {totales.por_estado
                .filter((e) => e.categoria === categoria)
                .map((e) => (
                  <div key={e.estado}>
                    <dt>{ETIQUETA_ESTADO[e.estado]}</dt>
                    <dd>{e.total}</dd>
                  </div>
                ))}
            </dl>
          </div>
        ))}
      </div>

      <h2>Reportes por semana</h2>
      <GraficaSemanal semanas={datos.por_semana} />

      <h2>Colonias con más baches abiertos</h2>
      {datos.top_colonias.length === 0 ? (
        <p>No hay baches abiertos.</p>
      ) : (
        <div className="tabla-desplazable">
          <table className="tabla-tablero">
            <caption>Las 10 colonias con más baches en Recibido, Validado o En reparación</caption>
            <thead>
              <tr>
                <th scope="col">Lugar</th>
                <th scope="col">Colonia</th>
                <th scope="col">Baches abiertos</th>
              </tr>
            </thead>
            <tbody>
              {datos.top_colonias.map((c, i) => (
                <tr key={c.colonia.id}>
                  <td>{i + 1}</td>
                  <td>{c.colonia.nombre}</td>
                  <td>{c.abiertos}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2>Baches abiertos más longevos</h2>
      {datos.mas_longevos.length === 0 ? (
        <p>No hay baches abiertos.</p>
      ) : (
        <div className="tabla-desplazable">
          <table className="tabla-tablero">
            <caption>Los 10 baches abiertos con más días desde que se reportaron</caption>
            <thead>
              <tr>
                <th scope="col">Folio</th>
                <th scope="col">Calle</th>
                <th scope="col">Colonia</th>
                <th scope="col">Estado</th>
                <th scope="col">Antigüedad</th>
              </tr>
            </thead>
            <tbody>
              {datos.mas_longevos.map((b) => (
                <tr key={b.id}>
                  <td>
                    <Link to={`/reportes/${b.id}`}>{b.folio}</Link>
                  </td>
                  <td>{b.calle}</td>
                  <td>{b.colonia.nombre}</td>
                  <td>{ETIQUETA_ESTADO[b.estado]}</td>
                  <td>{dias(b.antiguedad_dias)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2>Longevidad promedio por colonia</h2>
      {datos.longevidad_por_colonia.length === 0 ? (
        <p>No hay baches abiertos.</p>
      ) : (
        <div className="tabla-desplazable">
          <table className="tabla-tablero">
            <caption>Antigüedad promedio de los baches abiertos de cada colonia</caption>
            <thead>
              <tr>
                <th scope="col">Colonia</th>
                <th scope="col">Baches abiertos</th>
                <th scope="col">Promedio</th>
              </tr>
            </thead>
            <tbody>
              {datos.longevidad_por_colonia.map((c) => (
                <tr key={c.colonia.id}>
                  <td>{c.colonia.nombre}</td>
                  <td>{c.abiertos}</td>
                  <td>{dias(c.promedio_dias)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

interface PropsFiltros {
  inicial: Filtros
  onAplicar: (filtros: Filtros) => void
  onLimpiar: () => void
}

// Guarda lo que se va eligiendo y solo vuelve a pedir el tablero al presionar "Aplicar"
function FormularioFiltros({ inicial, onAplicar, onLimpiar }: PropsFiltros) {
  const [f, setF] = useState<Filtros>(inicial)
  const [errorFechas, setErrorFechas] = useState<string | undefined>()
  const sectores = useApi(() => pedirSectores(), [])
  const cambiar = (clave: keyof Filtros) => (valor: string) => setF((previo) => ({ ...previo, [clave]: valor }))

  function enviar(evento: FormEvent) {
    evento.preventDefault()
    if (f.desde && f.hasta && f.desde > f.hasta) {
      setErrorFechas('La fecha final no puede ser anterior a la inicial')
      return
    }
    setErrorFechas(undefined)
    onAplicar(f)
  }

  return (
    <form className="formulario filtros-tablero" onSubmit={enviar} aria-label="Filtros del tablero">
      <Campo id="tablero-desde" etiqueta="Desde" tipo="date" valor={f.desde} onCambio={cambiar('desde')} />
      <Campo
        id="tablero-hasta"
        etiqueta="Hasta"
        tipo="date"
        valor={f.hasta}
        onCambio={cambiar('hasta')}
        error={errorFechas}
      />
      <Campo
        id="tablero-sector"
        etiqueta="Sector"
        tipo="select"
        textoOpcionVacia="Todos"
        valor={f.sector_id}
        onCambio={cambiar('sector_id')}
        opciones={(sectores.datos ?? []).map((s) => ({ valor: String(s.id), etiqueta: s.nombre }))}
        ayuda={sectores.error ? 'No se pudo cargar la lista de sectores.' : undefined}
      />
      <div className="filtros-tablero-botones">
        <Boton type="submit">Aplicar</Boton>
        <Boton variante="secundario" onClick={onLimpiar}>
          Limpiar filtros
        </Boton>
      </div>
    </form>
  )
}
