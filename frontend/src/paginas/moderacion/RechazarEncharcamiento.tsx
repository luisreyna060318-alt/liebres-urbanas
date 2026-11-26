// RN-06: un moderador puede rechazar un encharcamiento (activo o histórico) en cualquier momento. La bandeja solo
// lista baches en Recibido, así que el botón vive en el detalle del reporte. El servidor vuelve a validar el rol y
// el estado; aquí solo se evita mostrar lo que no sirve.
import { useState } from 'react'
import { pedirMotivosRechazo } from '../../api/catalogos.ts'
import type { ReportePublico } from '../../api/tipos.ts'
import Alerta from '../../componentes/Alerta.tsx'
import Boton from '../../componentes/Boton.tsx'
import Estado from '../../componentes/Estado.tsx'
import { useApi } from '../../hooks/useApi.ts'
import type { PropsAccion } from './acciones.ts'
import FormularioRechazo from './FormularioRechazo.tsx'

interface Props {
  reporte: ReportePublico
  alCambiar: () => void // el reporte cambió: quien lo muestra vuelve a pedirlo
}

export default function RechazarEncharcamiento({ reporte, alCambiar }: Props) {
  const [abierto, setAbierto] = useState(false)
  const [mensaje, setMensaje] = useState<{ tipo: 'exito' | 'error'; texto: string } | null>(null)
  const rechazado = reporte.estado === 'rechazado'

  function terminar(tipo: 'exito' | 'error', texto: string) {
    setAbierto(false)
    setMensaje({ tipo, texto })
    alCambiar()
  }

  if (rechazado && !mensaje) return null

  return (
    <section className="rechazo-encharcamiento" aria-label="Moderación del reporte">
      {mensaje && <Alerta tipo={mensaje.tipo}>{mensaje.texto}</Alerta>}
      {!rechazado && !abierto && (
        <Boton
          variante="peligro"
          onClick={() => {
            setMensaje(null)
            setAbierto(true)
          }}
        >
          Rechazar este reporte
        </Boton>
      )}
      {!rechazado && abierto && (
        <ConMotivos
          reporte={reporte}
          alTerminar={(texto) => terminar('exito', texto)}
          alDesfasarse={(texto) => terminar('error', texto)}
          alCancelar={() => setAbierto(false)}
        />
      )}
    </section>
  )
}

// Los motivos se piden solo al abrir el formulario
function ConMotivos(props: PropsAccion) {
  const motivos = useApi(() => pedirMotivosRechazo())
  return (
    <Estado cargando={motivos.cargando} error={motivos.error} textoCargando="Cargando los motivos…" onReintentar={motivos.recargar}>
      <FormularioRechazo {...props} motivos={motivos.datos ?? []} />
    </Estado>
  )
}
