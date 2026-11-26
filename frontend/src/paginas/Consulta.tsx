// / (pública, HU-04.1 y HU-04.2): reportes activos sin cuenta, con filtros combinados, búsqueda por calle o folio
// y 20 por página. Los filtros viven en la URL (?categoria=bache&pagina=2) para poder compartir el enlace o recargar.
import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { pedirColonias } from '../api/catalogos.ts'
import { pedirReportes } from '../api/reportes.ts'
import type { Categoria, Estado as EstadoReporte, FiltroReportes, Severidad } from '../api/tipos.ts'
import Boton from '../componentes/Boton.tsx'
import Campo from '../componentes/Campo.tsx'
import Estado from '../componentes/Estado.tsx'
import Paginacion from '../componentes/Paginacion.tsx'
import TarjetaReporte from '../componentes/TarjetaReporte.tsx'
import { useAuth } from '../context/AuthContexto.ts'
import { useApi } from '../hooks/useApi.ts'
import { useTitulo } from '../hooks/useTitulo.ts'
import { ETIQUETA_CATEGORIA, ETIQUETA_ESTADO, ETIQUETA_SEVERIDAD, opcionesDe } from '../utils/etiquetas.ts'

// Filtros que se guardan en la URL (la página va aparte)
const CLAVES = ['categoria', 'estado', 'colonia_id', 'severidad', 'desde', 'hasta', 'q'] as const
type Filtros = Record<(typeof CLAVES)[number], string>

const FILTROS_VACIOS = Object.fromEntries(CLAVES.map((clave) => [clave, ''])) as Filtros

const ESTADOS_POR_CATEGORIA: Record<Categoria, EstadoReporte[]> = {
  bache: ['recibido', 'validado', 'en_reparacion', 'reparado'],
  encharcamiento: ['activo', 'historico'],
}

function leerFiltros(params: URLSearchParams): Filtros {
  return Object.fromEntries(CLAVES.map((clave) => [clave, params.get(clave) ?? ''])) as Filtros
}

// Texto de la URL -> filtro para la API. Los vacíos se quedan fuera (armarConsulta los omite).
function aFiltroApi(f: Filtros, pagina: number): FiltroReportes {
  return {
    categoria: (f.categoria || undefined) as Categoria | undefined,
    estado: (f.estado || undefined) as EstadoReporte | undefined,
    colonia_id: f.colonia_id ? Number(f.colonia_id) : undefined,
    severidad: (f.severidad || undefined) as Severidad | undefined,
    desde: f.desde || undefined,
    hasta: f.hasta || undefined,
    q: f.q.trim() || undefined,
    pagina,
  }
}

export default function Consulta() {
  useTitulo('Reportes')
  const [params, setParams] = useSearchParams()
  const filtros = leerFiltros(params)
  const pagina = Math.max(1, Math.floor(Number(params.get('pagina')) || 1))
  const hayFiltros = CLAVES.some((clave) => filtros[clave] !== '')

  const claveFiltros = CLAVES.map((c) => filtros[c]).join('|') // cambia solo cuando cambian los filtros
  const lista = useApi(() => pedirReportes(aFiltroApi(filtros, pagina)), [claveFiltros, pagina])

  // Escribe los filtros en la URL; la consulta se vuelve a pedir sola porque cambian las dependencias
  function aplicar(nuevos: Filtros, nuevaPagina = 1) {
    const siguiente = new URLSearchParams()
    for (const clave of CLAVES) if (nuevos[clave].trim()) siguiente.set(clave, nuevos[clave].trim())
    if (nuevaPagina > 1) siguiente.set('pagina', String(nuevaPagina))
    setParams(siguiente)
  }

  const limpiar = () => setParams(new URLSearchParams())
  const datos = lista.datos

  // Al cambiar de página la lista se reemplaza por "Cargando…" y el botón pulsado se desmonta; el foco pasa al
  // encabezado de resultados (que sigue montado) para no perderlo ni regresar al inicio de la página.
  const encabezadoResultados = useRef<HTMLHeadingElement>(null)
  function cambiarPagina(n: number) {
    encabezadoResultados.current?.focus()
    aplicar(filtros, n)
  }

  return (
    <section>
      <h1>Reportes</h1>
      <p>Baches y encharcamientos reportados por la ciudadanía. Por omisión se muestran los que siguen activos.</p>

      {/* El formulario no se desmonta al buscar (conserva el foco y las colonias ya pedidas); se resincroniza con la URL */}
      <FormularioFiltros clave={claveFiltros} inicial={filtros} onBuscar={(f) => aplicar(f)} onLimpiar={limpiar} />

      <h2 ref={encabezadoResultados} tabIndex={-1}>
        Resultados
      </h2>
      <Estado
        cargando={lista.cargando}
        error={lista.error}
        textoCargando="Cargando reportes…"
        onReintentar={lista.recargar}
      >
        {datos && datos.total === 0 ? (
          <div className="estado" role="status">
            <p>{hayFiltros ? 'No hay reportes que coincidan con los filtros.' : 'No hay reportes activos por ahora.'}</p>
            {hayFiltros && (
              <Boton variante="secundario" onClick={limpiar}>
                Limpiar filtros
              </Boton>
            )}
          </div>
        ) : (
          <>
            <ul className="lista-reportes">
              {datos?.items.map((r) => (
                <li key={r.id}>
                  <TarjetaReporte
                    reporte={r}
                    mostrarFecha
                    acciones={
                      <Link to={`/reportes/${r.id}`} className="boton boton-secundario">
                        Ver detalle <span className="solo-lectores">de {r.folio}</span>
                      </Link>
                    }
                  />
                </li>
              ))}
            </ul>
            {datos && (
              <Paginacion
                etiqueta="Páginas de reportes"
                pagina={datos.pagina}
                total={datos.total}
                tam={datos.tam}
                onCambiar={cambiarPagina}
              />
            )}
          </>
        )}
      </Estado>
    </section>
  )
}

interface PropsFiltros {
  clave: string // cambia cuando cambian los filtros de la URL (botón "atrás", "Limpiar filtros" de otro lado...)
  inicial: Filtros
  onBuscar: (filtros: Filtros) => void
  onLimpiar: () => void
}

// Formulario de filtros. Guarda lo que se va escribiendo y solo consulta al presionar "Buscar".
function FormularioFiltros({ clave, inicial, onBuscar, onLimpiar }: PropsFiltros) {
  const { usuario } = useAuth()
  const [f, setF] = useState<Filtros>(inicial)
  // Si la URL cambió por fuera del formulario, los campos vuelven a leerla (ajuste durante el render, sin efecto)
  const [errorFechas, setErrorFechas] = useState<string | undefined>()
  const [claveVista, setClaveVista] = useState(clave)
  if (clave !== claveVista) {
    setClaveVista(clave)
    setF(inicial)
    setErrorFechas(undefined)
  }
  const colonias = useApi(() => pedirColonias({ tam: 500 }), [])

  const cambiar = (clave: keyof Filtros) => (valor: string) => setF((previo) => ({ ...previo, [clave]: valor }))

  // Estados que tienen sentido para la categoría elegida. Los rechazados solo los consulta moderación;
  // el servidor lo vuelve a comprobar, esto solo evita ofrecer una opción que no sirve.
  const estados = f.categoria ? ESTADOS_POR_CATEGORIA[f.categoria as Categoria] : [...ESTADOS_POR_CATEGORIA.bache, ...ESTADOS_POR_CATEGORIA.encharcamiento]
  const veRechazados = usuario?.rol === 'moderador' || usuario?.rol === 'coordinador'
  const opcionesEstado = [...estados, ...(veRechazados ? (['rechazado'] as const) : [])].map((e) => ({
    valor: e,
    etiqueta: ETIQUETA_ESTADO[e],
  }))

  // También borra lo escrito sin aplicar: si la URL ya estaba sin filtros no cambia y el formulario no se resincroniza
  function limpiar() {
    setF(FILTROS_VACIOS)
    setErrorFechas(undefined)
    onLimpiar()
  }

  function enviar(evento: FormEvent) {
    evento.preventDefault()
    // Fechas AAAA-MM-DD: se comparan como texto
    if (f.desde && f.hasta && f.desde > f.hasta) {
      setErrorFechas('La fecha final no puede ser anterior a la inicial')
      return
    }
    setErrorFechas(undefined)
    onBuscar(f)
  }

  return (
    <form className="formulario filtros-consulta" onSubmit={enviar} aria-label="Filtros de reportes">
      <Campo
        id="filtro-q"
        etiqueta="Buscar por calle o folio"
        valor={f.q}
        onCambio={cambiar('q')}
        maxLength={100}
        ayuda="Por ejemplo: Tecnológico o BCH-2026-000123"
      />
      <Campo
        id="filtro-categoria"
        etiqueta="Tipo de reporte"
        tipo="select"
        textoOpcionVacia="Todos"
        valor={f.categoria}
        onCambio={(valor) => setF((previo) => ({ ...previo, categoria: valor, estado: '' }))}
        opciones={opcionesDe(ETIQUETA_CATEGORIA)}
      />
      <Campo
        id="filtro-estado"
        etiqueta="Estado"
        tipo="select"
        textoOpcionVacia="Activos"
        valor={f.estado}
        onCambio={cambiar('estado')}
        opciones={opcionesEstado}
      />
      <Campo
        id="filtro-colonia"
        etiqueta="Colonia"
        tipo="select"
        textoOpcionVacia="Todas"
        valor={f.colonia_id}
        onCambio={cambiar('colonia_id')}
        opciones={(colonias.datos?.items ?? []).map((c) => ({ valor: String(c.id), etiqueta: c.nombre }))}
        ayuda={colonias.error ? 'No se pudo cargar la lista de colonias.' : undefined}
      />
      <Campo
        id="filtro-severidad"
        etiqueta="Severidad"
        tipo="select"
        textoOpcionVacia="Todas"
        valor={f.severidad}
        onCambio={cambiar('severidad')}
        opciones={opcionesDe(ETIQUETA_SEVERIDAD)}
        ayuda="Solo aplica a baches"
      />
      <Campo id="filtro-desde" etiqueta="Desde" tipo="date" valor={f.desde} onCambio={cambiar('desde')} />
      <Campo id="filtro-hasta" etiqueta="Hasta" tipo="date" valor={f.hasta} onCambio={cambiar('hasta')} error={errorFechas} />

      <div className="filtros-consulta-botones">
        <Boton type="submit">Buscar</Boton>
        <Boton variante="secundario" onClick={limpiar}>
          Limpiar filtros
        </Boton>
      </div>
    </form>
  )
}
