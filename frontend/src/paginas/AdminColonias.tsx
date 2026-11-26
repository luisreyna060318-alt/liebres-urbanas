// /admin/colonias (solo coordinador, HU-06.1): catálogo de colonias y sectores.
// Muestra activas e inactivas, de 10 en 10. Una colonia con reportes no se puede eliminar (409): solo desactivar.
// El servidor vuelve a validar el rol y cada dato; esta pantalla solo facilita el trabajo.
import { useState } from 'react'
import { actualizarColonia, borrarColonia, pedirColonias, pedirSectores } from '../api/catalogos.ts'
import type { Colonia } from '../api/tipos.ts'
import Alerta from '../componentes/Alerta.tsx'
import Boton from '../componentes/Boton.tsx'
import Campo from '../componentes/Campo.tsx'
import Confirmar from '../componentes/Confirmar.tsx'
import Estado from '../componentes/Estado.tsx'
import FormularioColonia from '../componentes/FormularioColonia.tsx'
import Paginacion from '../componentes/Paginacion.tsx'
import SeccionSectores from '../componentes/SeccionSectores.tsx'
import { useApi } from '../hooks/useApi.ts'
import { useTitulo } from '../hooks/useTitulo.ts'

interface Mensaje {
  tipo: 'exito' | 'error'
  texto: string
}

export default function AdminColonias() {
  useTitulo('Administrar colonias')

  const [busqueda, setBusqueda] = useState('') // lo que se escribe
  const [q, setQ] = useState('') // lo que se busca (al presionar "Buscar")
  const [sectorId, setSectorId] = useState('')
  const [pagina, setPagina] = useState(1)

  const sectores = useApi(() => pedirSectores(), [])
  const lista = useApi(
    () => pedirColonias({ q, sector_id: sectorId ? Number(sectorId) : undefined, solo_activas: false, pagina, tam: 10 }),
    [q, sectorId, pagina],
  )

  const [editando, setEditando] = useState<Colonia | 'nueva' | null>(null)
  const [porBorrar, setPorBorrar] = useState<number | null>(null)
  const [ocupado, setOcupado] = useState(false)
  const [mensaje, setMensaje] = useState<Mensaje | null>(null)

  const items = lista.datos?.items ?? []
  const listaSectores = sectores.datos ?? []

  function buscar(e: React.SyntheticEvent) {
    e.preventDefault()
    setQ(busqueda.trim())
    setPagina(1)
  }

  function limpiarFiltros() {
    setBusqueda('')
    setQ('')
    setSectorId('')
    setPagina(1)
  }

  function alGuardar(colonia: Colonia, eraNueva: boolean) {
    setEditando(null)
    setMensaje({ tipo: 'exito', texto: eraNueva ? `Se creó la colonia ${colonia.nombre}.` : `Se guardaron los cambios de ${colonia.nombre}.` })
    lista.recargar()
  }

  function alCambiarSectores(texto: string) {
    setMensaje({ tipo: 'exito', texto })
    sectores.recargar()
    lista.recargar() // los nombres de sector de la tabla pueden haber cambiado
  }

  async function cambiarActiva(colonia: Colonia) {
    setOcupado(true)
    setMensaje(null)
    try {
      const nueva = !colonia.activa
      await actualizarColonia(colonia.id, {
        nombre: colonia.nombre,
        sector_id: colonia.sector.id,
        lat: colonia.lat,
        lon: colonia.lon,
        activa: nueva,
      })
      setMensaje({ tipo: 'exito', texto: `${colonia.nombre} quedó ${nueva ? 'activa' : 'inactiva'}.` })
      lista.recargar()
    } catch (e) {
      setMensaje({ tipo: 'error', texto: e instanceof Error ? e.message : 'No se pudo cambiar el estado.' })
    } finally {
      setOcupado(false)
    }
  }

  async function borrar(colonia: Colonia) {
    setOcupado(true)
    setMensaje(null)
    try {
      await borrarColonia(colonia.id)
      setMensaje({ tipo: 'exito', texto: `Se eliminó la colonia ${colonia.nombre}.` })
      // Si era la única de la última página, se regresa a la anterior
      if (items.length === 1 && pagina > 1) setPagina(pagina - 1)
      else lista.recargar()
    } catch (e) {
      // Con reportes el servidor responde 409 y explica que solo se puede desactivar
      setMensaje({ tipo: 'error', texto: e instanceof Error ? e.message : 'No se pudo eliminar la colonia.' })
    } finally {
      setOcupado(false)
      setPorBorrar(null)
    }
  }

  return (
    <section className="admin">
      <h1>Administrar colonias</h1>

      {mensaje && (
        <Alerta tipo={mensaje.tipo} onCerrar={() => setMensaje(null)}>
          {mensaje.texto}
        </Alerta>
      )}

      {editando ? (
        <FormularioColonia
          key={editando === 'nueva' ? 'nueva' : editando.id}
          colonia={editando === 'nueva' ? null : editando}
          sectores={listaSectores}
          alGuardar={alGuardar}
          alCancelar={() => setEditando(null)}
        />
      ) : (
        <p>
          <Boton onClick={() => setEditando('nueva')} disabled={listaSectores.length === 0}>
            Nueva colonia
          </Boton>
          {sectores.datos && listaSectores.length === 0 && <span> Primero crea un sector.</span>}
        </p>
      )}

      <form className="admin-filtros" role="search" aria-label="Buscar colonias" onSubmit={buscar}>
        <Campo id="filtro-q" etiqueta="Buscar por nombre" valor={busqueda} onCambio={setBusqueda} maxLength={100} />
        <Campo
          id="filtro-sector"
          etiqueta="Sector"
          tipo="select"
          valor={sectorId}
          onCambio={(valor) => {
            setSectorId(valor)
            setPagina(1)
          }}
          opciones={listaSectores.map((s) => ({ valor: String(s.id), etiqueta: s.nombre }))}
          textoOpcionVacia="Todos"
        />
        <div className="admin-filtros-botones">
          <Boton type="submit">Buscar</Boton>
          <Boton variante="secundario" onClick={limpiarFiltros}>
            Limpiar
          </Boton>
        </div>
      </form>

      <Estado
        cargando={lista.cargando}
        error={lista.error}
        vacio={lista.datos?.total === 0}
        textoCargando="Cargando colonias…"
        textoVacio={q || sectorId ? 'No hay colonias con esos filtros.' : 'Aún no hay colonias. Crea la primera.'}
        onReintentar={lista.recargar}
      >
        <div className="tabla-contenedor">
          <table className="tabla-admin">
            <caption>Colonias del catálogo (activas e inactivas)</caption>
            <thead>
              <tr>
                <th scope="col">Nombre</th>
                <th scope="col">Sector</th>
                <th scope="col">Estado</th>
                <th scope="col">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id}>
                  <th scope="row">{c.nombre}</th>
                  <td>{c.sector.nombre}</td>
                  <td>{c.activa ? 'Activa' : 'Inactiva'}</td>
                  <td>
                    {porBorrar === c.id ? (
                      <Confirmar
                        etiqueta={`Confirmar la eliminación de ${c.nombre}`}
                        mensaje={`¿Eliminar la colonia ${c.nombre}? No se puede deshacer.`}
                        textoConfirmar="Sí, eliminar"
                        textoCargando="Eliminando…"
                        variante="peligro"
                        ocupado={ocupado}
                        alConfirmar={() => void borrar(c)}
                        alCancelar={() => setPorBorrar(null)}
                      />
                    ) : (
                      <div className="tabla-acciones">
                        <Boton variante="secundario" onClick={() => setEditando(c)}>
                          Editar <span className="solo-lectores">{c.nombre}</span>
                        </Boton>
                        <Boton variante="secundario" onClick={() => void cambiarActiva(c)} disabled={ocupado}>
                          {c.activa ? 'Desactivar' : 'Activar'} <span className="solo-lectores">{c.nombre}</span>
                        </Boton>
                        <Boton variante="peligro" onClick={() => setPorBorrar(c.id)} disabled={ocupado}>
                          Eliminar <span className="solo-lectores">{c.nombre}</span>
                        </Boton>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {lista.datos && (
          <Paginacion
            etiqueta="Páginas de colonias"
            pagina={lista.datos.pagina}
            total={lista.datos.total}
            tam={lista.datos.tam}
            onCambiar={setPagina}
          />
        )}
      </Estado>

      <SeccionSectores sectores={listaSectores} alCambiar={alCambiarSectores} />
    </section>
  )
}
