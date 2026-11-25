import { useEffect, useRef } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContexto.ts'
import { ETIQUETA_ROL, opcionesParaRol } from '../utils/menu.ts'
import Alerta from './Alerta.tsx'
import Boton from './Boton.tsx'

// Estructura semántica común a todas las pantallas: header (con nav), main y footer
export default function Layout() {
  const { usuario, aviso, descartarAviso, logout } = useAuth()
  const navegar = useNavigate()
  const opciones = opcionesParaRol(usuario?.rol ?? null)

  // La app es una SPA: al cambiar de pantalla la página no se recarga y el foco se queda en el enlace pulsado
  // (que puede desaparecer). Se mueve el foco al contenido para que teclado y lector de pantalla empiecen ahí.
  const { pathname } = useLocation()
  const rutaAnterior = useRef(pathname)
  useEffect(() => {
    if (rutaAnterior.current === pathname) return // la primera carga no roba el foco
    rutaAnterior.current = pathname
    document.getElementById('contenido')?.focus()
  }, [pathname])

  function salir() {
    logout()
    navegar('/login')
  }

  return (
    <div className="app">
      <a className="saltar" href="#contenido">
        Saltar al contenido
      </a>

      <header className="encabezado">
        <div className="encabezado-barra">
          <Link to="/" className="marca">
            {/* El ícono es decorativo: el nombre del proyecto ya está escrito al lado */}
            <img src="/icono.svg" alt="" width="40" height="40" className="marca-icono" />
            Liebre Urbana
          </Link>

          {usuario && (
            <div className="sesion">
              <span className="sesion-nombre">
                {usuario.nombre} <small>Rol: {ETIQUETA_ROL[usuario.rol]}</small>
              </span>
              <Boton variante="secundario" onClick={salir}>
                Salir
              </Boton>
            </div>
          )}
        </div>

        {/* El menú solo muestra lo que el rol puede usar; el servidor vuelve a validar cada petición */}
        <nav className="navegacion" aria-label="Principal">
          <ul>
            {opciones.map((opcion) => (
              <li key={opcion.ruta}>
                <NavLink to={opcion.ruta} end>
                  {opcion.texto}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      {/* Aviso de sesión caducada o cerrada por inactividad */}
      {aviso && (
        <div className="aviso-sesion">
          <Alerta tipo="aviso" onCerrar={descartarAviso}>
            {aviso}
          </Alerta>
        </div>
      )}

      {/* tabIndex=-1 permite que "Saltar al contenido" y el cambio de pantalla muevan el foco aquí */}
      <main id="contenido" className="contenido" tabIndex={-1}>
        <Outlet />
      </main>

      <footer className="pie">
        <p>Liebre Urbana · Proyecto académico de Programación Web (AEB-1055) · ITCJ</p>
        <p>
          <Link to="/privacidad">Aviso de privacidad</Link>
        </p>
      </footer>
    </div>
  )
}
