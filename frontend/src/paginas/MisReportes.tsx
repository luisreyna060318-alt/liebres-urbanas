// /mis-reportes (solo ciudadano, HU-02.5): los reportes de la persona, 10 por página, con Editar y Eliminar
// solo mientras el reporte sigue en Recibido (`puede_editar`). El servidor vuelve a validarlo (409 REPORTE_NO_EDITABLE).
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ErrorApi } from '../api/cliente.ts'
import { borrarReporte, pedirMisReportes } from '../api/reportes.ts'
import type { ReporteMio } from '../api/tipos.ts'
import Alerta from '../componentes/Alerta.tsx'
import Boton from '../componentes/Boton.tsx'
import Confirmar from '../componentes/Confirmar.tsx'
import Estado from '../componentes/Estado.tsx'
import Paginacion from '../componentes/Paginacion.tsx'
import TarjetaReporte from '../componentes/TarjetaReporte.tsx'
import { useApi } from '../hooks/useApi.ts'
import { useTitulo } from '../hooks/useTitulo.ts'

interface Mensaje {
  tipo: 'exito' | 'error'
  texto: string
}

export default function MisReportes() {
  useTitulo('Mis reportes')
  const ubicacion = useLocation()

  const [pagina, setPagina] = useState(1)
  const lista = useApi(() => pedirMisReportes(pagina), [pagina])

  const [porBorrar, setPorBorrar] = useState<number | null>(null) // id del reporte que espera confirmación
  const [borrando, setBorrando] = useState(false)
  const [mensaje, setMensaje] = useState<Mensaje | null>(null)

  // Al guardar una edición, la pantalla anterior manda el aviso de éxito en el estado de la navegación
  const avisoDeEdicion = (ubicacion.state as { aviso?: string } | null)?.aviso

  const items = lista.datos?.items ?? []

  async function borrar(reporte: ReporteMio) {
    setBorrando(true)
    setMensaje(null)
    try {
      await borrarReporte(reporte.id)
      setMensaje({ tipo: 'exito', texto: `Se eliminó el reporte ${reporte.folio}.` })
      // Si era el único de la última página, se regresa a la anterior (el cambio de página ya vuelve a pedir la lista)
      if (items.length === 1 && pagina > 1) setPagina(pagina - 1)
      else lista.recargar()
    } catch (e) {
      const texto = e instanceof Error ? e.message : 'No se pudo eliminar el reporte.'
      setMensaje({ tipo: 'error', texto })
      // Si ya no estaba en Recibido, la lista se refresca para que los botones desaparezcan
      if (e instanceof ErrorApi && e.codigo === 'REPORTE_NO_EDITABLE') lista.recargar()
    } finally {
      setBorrando(false)
      setPorBorrar(null)
    }
  }

  return (
    <section>
      <h1>Mis reportes</h1>

      {avisoDeEdicion && <Alerta tipo="exito">{avisoDeEdicion}</Alerta>}
      {mensaje && (
        <Alerta tipo={mensaje.tipo} onCerrar={() => setMensaje(null)}>
          {mensaje.texto}
        </Alerta>
      )}

      <Estado
        cargando={lista.cargando}
        error={lista.error}
        vacio={lista.datos?.total === 0}
        textoCargando="Cargando tus reportes…"
        textoVacio="Aún no tienes reportes. Cuando reportes un bache o un encharcamiento, aparecerá aquí."
        onReintentar={lista.recargar}
      >
        <h2 className="solo-lectores">Lista de tus reportes</h2>
        <ul className="lista-reportes">
          {items.map((r) => (
            <li key={r.id}>
              <TarjetaReporte
                reporte={r}
                mostrarFecha
                acciones={
                  r.puede_editar &&
                  (porBorrar === r.id ? (
                    <Confirmar
                      etiqueta={`Confirmar la eliminación de ${r.folio}`}
                      mensaje={`¿Eliminar el reporte ${r.folio}? Esta acción no se puede deshacer.`}
                      textoConfirmar="Sí, eliminar"
                      textoCargando="Eliminando…"
                      variante="peligro"
                      ocupado={borrando}
                      alConfirmar={() => void borrar(r)}
                      alCancelar={() => setPorBorrar(null)}
                    />
                  ) : (
                    <>
                      <Link to={`/mis-reportes/${r.id}/editar`} className="boton boton-secundario">
                        Editar <span className="solo-lectores">{r.folio}</span>
                      </Link>
                      <Boton variante="peligro" onClick={() => setPorBorrar(r.id)}>
                        Eliminar <span className="solo-lectores">{r.folio}</span>
                      </Boton>
                    </>
                  ))
                }
              >
                {/* El motivo lo escribe quien moderó; así la persona sabe por qué no avanzó su reporte */}
                {r.estado === 'rechazado' && r.motivo_rechazo && (
                  <p className="motivo-rechazo">
                    <strong>Motivo del rechazo:</strong> {r.motivo_rechazo.nombre}
                    {r.motivo_rechazo.texto && `. ${r.motivo_rechazo.texto}`}
                  </p>
                )}
              </TarjetaReporte>
            </li>
          ))}
        </ul>

        {lista.datos && (
          <Paginacion
            etiqueta="Páginas de mis reportes"
            pagina={lista.datos.pagina}
            total={lista.datos.total}
            tam={lista.datos.tam}
            onCambiar={setPagina}
          />
        )}
      </Estado>

      {/* Con reportes o sin ellos, siempre hay un camino para crear otro */}
      <p className="enlace-aparte">
        <Link to="/reportar" className="boton">
          {lista.datos?.total === 0 ? 'Crear mi primer reporte' : 'Reportar un problema'}
        </Link>
      </p>
    </section>
  )
}
