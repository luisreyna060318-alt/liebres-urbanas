import { Link, Navigate, Outlet, useLocation } from 'react-router-dom'
import type { Rol } from '../api/tipos.ts'
import { useAuth } from '../context/AuthContexto.ts'
import { useTitulo } from '../hooks/useTitulo.ts'

interface Props {
  roles?: readonly Rol[] // roles que pueden entrar; si no se indica, basta con haber iniciado sesión
}

// Protege un grupo de rutas (se usa como `element` de una ruta que contiene a las demás).
// Ocultar enlaces no es seguridad: el servidor vuelve a validar el rol en cada petición.
export default function RutaPrivada({ roles }: Props) {
  const { usuario, cargando, salioPorSuCuenta, tienePermiso } = useAuth()
  const ubicacion = useLocation()

  // Aún se comprueba el token guardado: no se redirige todavía
  if (cargando) {
    return (
      <div className="estado" role="status">
        <p>Cargando…</p>
      </div>
    )
  }

  // Sin sesión: a /login, recordando a dónde quería ir. Si la persona salió por su cuenta no se recuerda:
  // quien entre después en el mismo equipo (quizá con otro rol) debe llegar al inicio, no a esa pantalla.
  if (!usuario) {
    const estado = salioPorSuCuenta ? null : { desde: ubicacion.pathname + ubicacion.search }
    return <Navigate to="/login" replace state={estado} />
  }

  if (roles && !tienePermiso(roles)) return <SinPermiso />

  return <Outlet />
}

function SinPermiso() {
  useTitulo('Sin permiso')

  return (
    <section>
      <h1>No tienes permiso</h1>
      <p role="alert">Tu cuenta no puede usar esta sección.</p>
      <p>
        <Link to="/">Volver al inicio</Link>
      </p>
    </section>
  )
}
