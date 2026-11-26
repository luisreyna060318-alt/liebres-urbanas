// Pestaña "En seguimiento" (HU-05.2): baches validados y en reparación, del más antiguo al más reciente, con los
// botones "Marcar en reparación" (desde Validado) y "Marcar reparado" (desde En reparación), como pide RN-05.
import { useState } from 'react'
import { pedirColonias, pedirTiposDano } from '../../api/catalogos.ts'
import { pedirSeguimiento } from '../../api/moderacion.ts'
import type { EstadoAvance, ReportePublico } from '../../api/tipos.ts'
import Alerta from '../../componentes/Alerta.tsx'
import Boton from '../../componentes/Boton.tsx'
import Estado from '../../componentes/Estado.tsx'
import Paginacion from '../../componentes/Paginacion.tsx'
import TarjetaReporte from '../../componentes/TarjetaReporte.tsx'
import { useApi } from '../../hooks/useApi.ts'
import DatosParaRevisar from './DatosParaRevisar.tsx'
import FiltrosModeracion from './FiltrosModeracion.tsx'
import type { Filtros } from './FiltrosModeracion.tsx'
import FormularioAvance from './FormularioAvance.tsx'

interface Mensaje {
  tipo: 'exito' | 'error'
  texto: string
}

// El único paso siguiente de cada estado (RN-05)
const SIGUIENTE: Partial<Record<ReportePublico['estado'], { estado: EstadoAvance; texto: string }>> = {
  validado: { estado: 'en_reparacion', texto: 'Marcar en reparación' },
  en_reparacion: { estado: 'reparado', texto: 'Marcar reparado' },
}

export default function EnSeguimiento() {
  const [filtros, setFiltros] = useState<Filtros>({ colonia_id: '', tipo_dano_codigo: '' })
  const [pagina, setPagina] = useState(1)
  const lista = useApi(
    () =>
      pedirSeguimiento({
        colonia_id: filtros.colonia_id ? Number(filtros.colonia_id) : undefined,
        tipo_dano_codigo: filtros.tipo_dano_codigo || undefined,
        pagina,
      }),
    [filtros, pagina],
  )
  const colonias = useApi(() => pedirColonias({ tam: 500 }))
  const tipos = useApi(() => pedirTiposDano())

  const [abierto, setAbierto] = useState<number | null>(null) // id del reporte con el formulario abierto
  const [mensaje, setMensaje] = useState<Mensaje | null>(null)
  const items = lista.datos?.items ?? []

  function cambiarFiltros(nuevos: Filtros) {
    setFiltros(nuevos)
    setPagina(1)
    setAbierto(null)
  }

  // Un bache reparado sale de la lista; uno en reparación cambia de botón: en ambos casos se vuelve a pedir.
  // Si salía el único de la última página, se regresa a la anterior (como en "Por revisar"); el cambio de página
  // ya vuelve a pedir la lista.
  function refrescar(nuevo: Mensaje, saleDeLaLista: boolean) {
    setMensaje(nuevo)
    setAbierto(null)
    if (saleDeLaLista && items.length === 1 && pagina > 1) setPagina(pagina - 1)
    else lista.recargar()
  }

  function acciones(r: ReportePublico) {
    const siguiente = SIGUIENTE[r.estado]
    if (!siguiente) return null
    if (abierto === r.id) {
      const sale = siguiente.estado === 'reparado' // solo "reparado" saca el bache de esta lista
      return (
        <FormularioAvance
          reporte={r}
          estado={siguiente.estado}
          alTerminar={(texto) => refrescar({ tipo: 'exito', texto }, sale)}
          alDesfasarse={(texto) => refrescar({ tipo: 'error', texto }, sale)}
          alCancelar={() => setAbierto(null)}
        />
      )
    }
    return (
      <Boton onClick={() => setAbierto(r.id)}>
        {siguiente.texto} <span className="solo-lectores">{r.folio}</span>
      </Boton>
    )
  }

  return (
    <>
      <p>Baches validados y en reparación, del más antiguo al más reciente.</p>
      <FiltrosModeracion
        idBase="seguimiento"
        filtros={filtros}
        onCambiar={cambiarFiltros}
        colonias={colonias.datos?.items ?? []}
        tipos={tipos.datos ?? []}
        errorCatalogos={colonias.error ?? tipos.error}
      />

      {mensaje && (
        <Alerta tipo={mensaje.tipo} onCerrar={() => setMensaje(null)}>
          {mensaje.texto}
        </Alerta>
      )}

      <Estado
        cargando={lista.cargando}
        error={lista.error}
        vacio={lista.datos?.total === 0}
        textoCargando="Cargando los baches en seguimiento…"
        textoVacio="No hay baches validados ni en reparación."
        onReintentar={lista.recargar}
      >
        <ul className="lista-reportes">
          {items.map((r) => (
            <li key={r.id}>
              <TarjetaReporte reporte={r} mostrarFecha acciones={acciones(r)}>
                <DatosParaRevisar reporte={r} />
              </TarjetaReporte>
            </li>
          ))}
        </ul>
        {lista.datos && (
          <Paginacion
            etiqueta="Páginas de baches en seguimiento"
            pagina={lista.datos.pagina}
            total={lista.datos.total}
            tam={lista.datos.tam}
            onCambiar={setPagina}
          />
        )}
      </Estado>
    </>
  )
}
