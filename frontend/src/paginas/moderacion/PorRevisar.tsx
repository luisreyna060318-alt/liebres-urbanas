// Pestaña "Por revisar" (HU-05.1): baches en Recibido, del más antiguo al más reciente, con filtros por colonia y
// tipo de daño, 10 por página, y los botones Validar y Rechazar. El servidor decide (solo moderador, 403 a los demás).
import { useState } from 'react'
import { pedirColonias, pedirMotivosRechazo, pedirTiposDano } from '../../api/catalogos.ts'
import { pedirBandeja } from '../../api/moderacion.ts'
import type { ReportePublico } from '../../api/tipos.ts'
import Alerta from '../../componentes/Alerta.tsx'
import Boton from '../../componentes/Boton.tsx'
import Estado from '../../componentes/Estado.tsx'
import Paginacion from '../../componentes/Paginacion.tsx'
import TarjetaReporte from '../../componentes/TarjetaReporte.tsx'
import { useApi } from '../../hooks/useApi.ts'
import DatosParaRevisar from './DatosParaRevisar.tsx'
import FiltrosModeracion from './FiltrosModeracion.tsx'
import type { Filtros } from './FiltrosModeracion.tsx'
import FormularioRechazo from './FormularioRechazo.tsx'
import FormularioValidar from './FormularioValidar.tsx'

interface Abierto {
  id: number
  accion: 'validar' | 'rechazar'
}

interface Mensaje {
  tipo: 'exito' | 'error'
  texto: string
}

export default function PorRevisar() {
  const [filtros, setFiltros] = useState<Filtros>({ colonia_id: '', tipo_dano_codigo: '' })
  const [pagina, setPagina] = useState(1)
  const lista = useApi(
    () =>
      pedirBandeja({
        colonia_id: filtros.colonia_id ? Number(filtros.colonia_id) : undefined,
        tipo_dano_codigo: filtros.tipo_dano_codigo || undefined,
        pagina,
      }),
    [filtros, pagina],
  )
  const motivos = useApi(() => pedirMotivosRechazo())
  const colonias = useApi(() => pedirColonias({ tam: 500 }))
  const tipos = useApi(() => pedirTiposDano())

  const [abierto, setAbierto] = useState<Abierto | null>(null)
  const [mensaje, setMensaje] = useState<Mensaje | null>(null)
  const items = lista.datos?.items ?? []

  function cambiarFiltros(nuevos: Filtros) {
    setFiltros(nuevos)
    setPagina(1)
    setAbierto(null)
  }

  // Después de validar o rechazar, el reporte sale de la bandeja: se vuelve a pedir la página
  function refrescar(nuevo: Mensaje) {
    setMensaje(nuevo)
    setAbierto(null)
    if (items.length === 1 && pagina > 1) setPagina(pagina - 1)
    else lista.recargar()
  }

  function acciones(r: ReportePublico) {
    const props = {
      reporte: r,
      alTerminar: (texto: string) => refrescar({ tipo: 'exito', texto }),
      alDesfasarse: (texto: string) => refrescar({ tipo: 'error', texto }),
      alCancelar: () => setAbierto(null),
    }
    if (abierto?.id === r.id && abierto.accion === 'validar') return <FormularioValidar {...props} />
    if (abierto?.id === r.id && abierto.accion === 'rechazar') {
      return (
        <Estado
          cargando={motivos.cargando}
          error={motivos.error}
          vacio={motivos.datos?.length === 0}
          textoCargando="Cargando motivos de rechazo…"
          textoVacio="No hay motivos de rechazo activos. Pide a coordinación que los configure."
          onReintentar={motivos.recargar}
        >
          <FormularioRechazo {...props} motivos={motivos.datos ?? []} />
        </Estado>
      )
    }
    return (
      <>
        <Boton onClick={() => setAbierto({ id: r.id, accion: 'validar' })}>
          Validar <span className="solo-lectores">{r.folio}</span>
        </Boton>
        <Boton variante="peligro" onClick={() => setAbierto({ id: r.id, accion: 'rechazar' })}>
          Rechazar <span className="solo-lectores">{r.folio}</span>
        </Boton>
      </>
    )
  }

  return (
    <>
      <p>Baches nuevos que esperan revisión, del más antiguo al más reciente.</p>
      <FiltrosModeracion
        idBase="revisar"
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
        textoCargando="Cargando la bandeja…"
        textoVacio="No hay reportes por revisar."
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
            etiqueta="Páginas de reportes por revisar"
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
