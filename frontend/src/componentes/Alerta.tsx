import type { ReactNode } from 'react'
import Boton from './Boton.tsx'

type Tipo = 'error' | 'exito' | 'aviso' | 'info'

interface Props {
  tipo?: Tipo
  children: ReactNode
  onCerrar?: () => void // si se pasa, aparece el botón "Cerrar aviso"
}

// Cada tipo lleva una palabra y un símbolo además del color, para que nadie dependa solo de distinguir colores
const ROTULOS: Record<Tipo, { simbolo: string; texto: string }> = {
  error: { simbolo: '✖', texto: 'Error' },
  exito: { simbolo: '✔', texto: 'Listo' },
  aviso: { simbolo: '⚠', texto: 'Aviso' },
  info: { simbolo: 'ℹ', texto: 'Información' },
}

// Mensaje destacado. Los errores usan role="alert" (se anuncian de inmediato); lo demás, role="status".
export default function Alerta({ tipo = 'info', children, onCerrar }: Props) {
  const rotulo = ROTULOS[tipo]

  return (
    <div className={`alerta alerta-${tipo}`} role={tipo === 'error' ? 'alert' : 'status'}>
      <strong className="alerta-icono">
        <span aria-hidden="true">{rotulo.simbolo} </span>
        {rotulo.texto}:
      </strong>
      <div className="alerta-contenido">{children}</div>
      {onCerrar && (
        <Boton variante="secundario" onClick={onCerrar}>
          Cerrar aviso
        </Boton>
      )}
    </div>
  )
}
