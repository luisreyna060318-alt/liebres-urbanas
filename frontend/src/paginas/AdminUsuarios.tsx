// /admin/usuarios (solo coordinador, HU-06.2): buscar cuentas, cambiar su rol y suspenderlas o reactivarlas.
// Cada cambio pide confirmación. El servidor decide: por ejemplo, rechaza (409) quitarle el rol o suspender al
// último coordinador activo, y esta pantalla muestra su mensaje tal cual.
import { useState } from 'react'
import { cambiarRol, cambiarSuspension, pedirUsuarios } from '../api/usuarios.ts'
import { ROLES } from '../api/tipos.ts'
import type { Rol, UsuarioAdmin } from '../api/tipos.ts'
import Alerta from '../componentes/Alerta.tsx'
import Boton from '../componentes/Boton.tsx'
import Campo from '../componentes/Campo.tsx'
import Confirmar from '../componentes/Confirmar.tsx'
import Estado from '../componentes/Estado.tsx'
import Paginacion from '../componentes/Paginacion.tsx'
import { useAuth } from '../context/AuthContexto.ts'
import { useApi } from '../hooks/useApi.ts'
import { useTitulo } from '../hooks/useTitulo.ts'
import { formatoFecha } from '../utils/fechas.ts'

const ETIQUETA_ROL: Record<Rol, string> = { ciudadano: 'Ciudadano', moderador: 'Moderador', coordinador: 'Coordinador' }
const OPCIONES_ROL = ROLES.map((r) => ({ valor: r, etiqueta: ETIQUETA_ROL[r] }))

// Lo que espera confirmación: cambiar el rol de una cuenta o suspenderla/reactivarla
type Pendiente = { id: number; tipo: 'rol'; rol: Rol } | { id: number; tipo: 'suspension'; suspendido: boolean }

interface Mensaje {
  tipo: 'exito' | 'error'
  texto: string
}

export default function AdminUsuarios() {
  useTitulo('Administrar usuarios')
  const { usuario: yo } = useAuth()

  const [busqueda, setBusqueda] = useState('') // lo que se escribe
  const [q, setQ] = useState('') // lo que se busca (al presionar "Buscar")
  const [rolFiltro, setRolFiltro] = useState('')
  const [pagina, setPagina] = useState(1)
  const lista = useApi(
    () => pedirUsuarios({ q, rol: rolFiltro as Rol | '', pagina, tam: 10 }),
    [q, rolFiltro, pagina],
  )

  const [pendiente, setPendiente] = useState<Pendiente | null>(null)
  const [ocupado, setOcupado] = useState(false)
  const [mensaje, setMensaje] = useState<Mensaje | null>(null)

  const items = lista.datos?.items ?? []

  function buscar(e: React.SyntheticEvent) {
    e.preventDefault()
    setQ(busqueda.trim())
    setPagina(1)
  }

  function limpiarFiltros() {
    setBusqueda('')
    setQ('')
    setRolFiltro('')
    setPagina(1)
  }

  async function confirmar(cuenta: UsuarioAdmin, accion: Pendiente) {
    setOcupado(true)
    setMensaje(null)
    try {
      if (accion.tipo === 'rol') {
        await cambiarRol(cuenta.id, accion.rol)
        setMensaje({ tipo: 'exito', texto: `${cuenta.nombre} ahora es ${ETIQUETA_ROL[accion.rol].toLowerCase()}.` })
      } else {
        await cambiarSuspension(cuenta.id, accion.suspendido)
        const hecho = accion.suspendido ? 'quedó suspendida' : 'quedó reactivada'
        setMensaje({ tipo: 'exito', texto: `La cuenta de ${cuenta.nombre} ${hecho}.` })
      }
    } catch (e) {
      // Por ejemplo el 409 "Es el último coordinador activo..."
      setMensaje({ tipo: 'error', texto: e instanceof Error ? e.message : 'No se pudo guardar el cambio.' })
    } finally {
      setOcupado(false)
      setPendiente(null)
      lista.recargar() // se vuelve a leer del servidor, que es quien decide cómo quedó cada cuenta
    }
  }

  return (
    <section className="admin-usuarios">
      <h1>Administrar usuarios</h1>

      {mensaje && (
        <Alerta tipo={mensaje.tipo} onCerrar={() => setMensaje(null)}>
          {mensaje.texto}
        </Alerta>
      )}

      <form className="filtros-usuarios" role="search" aria-label="Buscar usuarios" onSubmit={buscar}>
        <Campo id="filtro-q" etiqueta="Buscar por nombre o correo" valor={busqueda} onCambio={setBusqueda} maxLength={100} />
        <Campo
          id="filtro-rol"
          etiqueta="Rol"
          tipo="select"
          valor={rolFiltro}
          onCambio={(valor) => {
            setRolFiltro(valor)
            setPagina(1)
          }}
          opciones={OPCIONES_ROL}
          textoOpcionVacia="Todos"
        />
        <div className="filtros-usuarios-botones">
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
        textoCargando="Cargando usuarios…"
        textoVacio={q || rolFiltro ? 'No hay usuarios con esos filtros.' : 'Aún no hay usuarios.'}
        onReintentar={lista.recargar}
      >
        <div className="tabla-usuarios-contenedor">
          <table className="tabla-usuarios">
            <caption>Cuentas de la plataforma</caption>
            <thead>
              <tr>
                <th scope="col">Nombre</th>
                <th scope="col">Correo</th>
                <th scope="col">Rol</th>
                <th scope="col">Estado</th>
                <th scope="col">Alta</th>
                <th scope="col">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.map((u) => (
                <tr key={u.id}>
                  <th scope="row">
                    {u.nombre}
                    {yo?.id === u.id && ' (tú)'}
                  </th>
                  <td className="tabla-usuarios-correo">{u.correo}</td>
                  <td>
                    <label className="solo-lectores" htmlFor={`rol-${u.id}`}>
                      Rol de {u.nombre}
                    </label>
                    <select
                      id={`rol-${u.id}`}
                      className="selector-rol"
                      value={u.rol}
                      disabled={ocupado}
                      onChange={(e) => setPendiente({ id: u.id, tipo: 'rol', rol: e.target.value as Rol })}
                    >
                      {OPCIONES_ROL.map((o) => (
                        <option key={o.valor} value={o.valor}>
                          {o.etiqueta}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>{u.activo ? 'Activa' : 'Suspendida'}</td>
                  <td>{formatoFecha(u.creado_en)}</td>
                  <td>
                    {pendiente?.id === u.id ? (
                      <Confirmar
                        etiqueta="Confirmar el cambio"
                        mensaje={preguntaDe(u, pendiente)}
                        textoConfirmar="Sí, confirmar"
                        textoCargando="Guardando…"
                        ocupado={ocupado}
                        alConfirmar={() => void confirmar(u, pendiente)}
                        alCancelar={() => setPendiente(null)}
                      />
                    ) : (
                      <Boton
                        variante={u.activo ? 'peligro' : 'secundario'}
                        disabled={ocupado}
                        onClick={() => setPendiente({ id: u.id, tipo: 'suspension', suspendido: u.activo })}
                      >
                        {u.activo ? 'Suspender' : 'Reactivar'} <span className="solo-lectores">a {u.nombre}</span>
                      </Boton>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {lista.datos && (
          <Paginacion
            etiqueta="Páginas de usuarios"
            pagina={lista.datos.pagina}
            total={lista.datos.total}
            tam={lista.datos.tam}
            onCambiar={setPagina}
          />
        )}
      </Estado>
    </section>
  )
}

function preguntaDe(cuenta: UsuarioAdmin, accion: Pendiente): string {
  if (accion.tipo === 'rol') return `¿Cambiar el rol de ${cuenta.nombre} a ${ETIQUETA_ROL[accion.rol].toLowerCase()}?`
  return accion.suspendido
    ? `¿Suspender la cuenta de ${cuenta.nombre}? No podrá iniciar sesión; sus reportes se conservan.`
    : `¿Reactivar la cuenta de ${cuenta.nombre}?`
}
