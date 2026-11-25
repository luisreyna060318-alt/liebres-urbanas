import { Link } from 'react-router-dom'
import { pedirAvisoLluvia } from '../api/clima.ts'
import { useApi } from '../hooks/useApi.ts'
import Alerta from './Alerta.tsx'

// Franja de la parte de arriba (HU-08.1). Tres resultados posibles:
//  - hay probabilidad de lluvia >= umbral: aviso con enlace a "¿Cómo está mi zona?"
//  - sin lluvia: no se muestra nada (CA2)
//  - el pronóstico falló (la API responde disponible: false, o ni siquiera responde): texto discreto, sin romper nada (CA4)
// Mientras carga tampoco se muestra nada: un aviso secundario no debe mover la pantalla ni quitarle el foco a lo principal.
export default function AvisoLluvia() {
  const { datos, cargando, error } = useApi(pedirAvisoLluvia)

  if (cargando) return null

  if (error || !datos || !datos.disponible) {
    return (
      <div className="aviso-clima">
        <p className="pronostico-no-disponible">Pronóstico no disponible</p>
      </div>
    )
  }

  if (!datos.hay_aviso) return null

  return (
    <div className="aviso-clima">
      <Alerta tipo="aviso">
        <p>
          Posible lluvia en las próximas {datos.horas} horas (probabilidad máxima de {datos.probabilidad_max_pct} %).
          Revisa cómo está tu zona antes de salir.{' '}
          <Link to="/zona">Ver cómo está mi zona</Link>
        </p>
      </Alerta>
    </div>
  )
}
