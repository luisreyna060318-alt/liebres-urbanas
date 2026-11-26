import { Route, Routes } from 'react-router-dom'
import Layout from './componentes/Layout.tsx'
import RutaPrivada from './componentes/RutaPrivada.tsx'
import AdminColonias from './paginas/AdminColonias.tsx'
import AdminUsuarios from './paginas/AdminUsuarios.tsx'
import Consulta from './paginas/Consulta.tsx'
import DetalleReporte from './paginas/DetalleReporte.tsx'
import EditarReporte from './paginas/EditarReporte.tsx'
import Login from './paginas/Login.tsx'
import Mapa from './paginas/Mapa.tsx'
import MisReportes from './paginas/MisReportes.tsx'
import Moderacion from './paginas/Moderacion.tsx'
import NoEncontrada from './paginas/NoEncontrada.tsx'
import Perfil from './paginas/Perfil.tsx'
import Privacidad from './paginas/Privacidad.tsx'
import Registro from './paginas/Registro.tsx'
import Reportar from './paginas/Reportar.tsx'
import Tablero from './paginas/Tablero.tsx'
import Zona from './paginas/Zona.tsx'
import { ROLES_CIUDADANO, ROLES_COORDINADOR, ROLES_SEGUIMIENTO } from './utils/menu.ts'

// Todas las rutas comparten el Layout (header, nav, main, footer).
// Las rutas privadas piden sesión y rol aquí; el servidor vuelve a validar el rol en cada petición.
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        {/* Públicas */}
        <Route path="/" element={<Consulta />} />
        <Route path="/zona" element={<Zona />} />
        <Route path="/mapa" element={<Mapa />} />
        <Route path="/reportes/:id" element={<DetalleReporte />} />
        <Route path="/login" element={<Login />} />
        <Route path="/registro" element={<Registro />} />
        <Route path="/privacidad" element={<Privacidad />} />

        {/* Ciudadano */}
        <Route element={<RutaPrivada roles={ROLES_CIUDADANO} />}>
          <Route path="/reportar" element={<Reportar />} />
          <Route path="/mis-reportes" element={<MisReportes />} />
          <Route path="/mis-reportes/:id/editar" element={<EditarReporte />} />
          <Route path="/perfil" element={<Perfil />} />
        </Route>

        {/* Moderador */}
        <Route element={<RutaPrivada roles={ROLES_SEGUIMIENTO} />}>
          <Route path="/moderacion" element={<Moderacion />} />
        </Route>

        {/* Coordinador */}
        <Route element={<RutaPrivada roles={ROLES_COORDINADOR} />}>
          <Route path="/admin/colonias" element={<AdminColonias />} />
          <Route path="/admin/usuarios" element={<AdminUsuarios />} />
          <Route path="/tablero" element={<Tablero />} />
        </Route>

        <Route path="*" element={<NoEncontrada />} />
      </Route>
    </Routes>
  )
}
