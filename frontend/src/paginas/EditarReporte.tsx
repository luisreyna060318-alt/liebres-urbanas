// /mis-reportes/:id/editar (solo ciudadano, HU-02.5): el mismo formulario de bache, precargado con el reporte.
// Solo se puede editar un bache en Recibido; el servidor lo valida otra vez (409 REPORTE_NO_EDITABLE).
import { Link, useNavigate, useParams } from 'react-router-dom'
import { pedirDetalle } from '../api/reportes.ts'
import Alerta from '../componentes/Alerta.tsx'
import Estado from '../componentes/Estado.tsx'
import FormularioBache from '../componentes/FormularioBache.tsx'
import { useApi } from '../hooks/useApi.ts'
import { useTitulo } from '../hooks/useTitulo.ts'

export default function EditarReporte() {
  useTitulo('Editar reporte')
  const { id } = useParams()
  const navegar = useNavigate()
  const numero = Number(id)

  // El id viene de la URL: si no es un número entero positivo no se llama a la API
  const idValido = Number.isInteger(numero) && numero > 0
  const detalle = useApi(() => (idValido ? pedirDetalle(numero) : Promise.reject(new Error('Ese reporte no existe.'))), [numero])
  const reporte = detalle.datos

  return (
    <section>
      <h1>Editar reporte</h1>
      <p>
        <Link to="/mis-reportes">Volver a Mis reportes</Link>
      </p>

      <Estado
        cargando={detalle.cargando}
        error={detalle.error}
        textoCargando="Cargando el reporte…"
        onReintentar={detalle.recargar}
      >
        {reporte && reporte.categoria === 'bache' && reporte.estado === 'recibido' ? (
          <FormularioBache
            reporte={reporte}
            alGuardar={(guardado) =>
              navegar('/mis-reportes', { state: { aviso: `Se guardaron los cambios del reporte ${guardado.folio}.` } })
            }
          />
        ) : (
          reporte && (
            <Alerta tipo="aviso">
              El reporte {reporte.folio} ya no se puede editar porque dejó de estar en Recibido.
            </Alerta>
          )
        )}
      </Estado>
    </section>
  )
}
