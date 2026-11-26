// Botones para responder sobre un reporte ajeno (HU-03.3 y confirmaciones de baches de HU-02.3).
//
// CÓMO USARLO (por ejemplo en la pantalla de detalle):
//   <AccionesConfirmacion reporte={reporte} alActualizar={(actualizado) => setReporte(actualizado)} />
//   - `reporte`: cualquier ReportePublico (o ReporteDetalle). Según su categoría y estado el componente decide qué mostrar:
//       encharcamiento activo -> "Sigue ahí" y "Ya no hay agua"
//       bache abierto         -> "Confirmar que sigue ahí"
//       cualquier otro caso   -> no muestra nada (reparado, histórico, rechazado)
//   - `alActualizar`: se llama con el ReportePublico actualizado que devuelve el servidor (confirmaciones, vigente_hasta,
//     estado...). La pantalla que lo usa solo tiene que guardarlo en su estado; ya no hace falta volver a pedir el detalle.
//   - Sin sesión invita a iniciar sesión; con un rol distinto de ciudadano avisa que no puede confirmar.
//   - Si el servidor responde 409 YA_CONFIRMADO ("Ya respondiste sobre este reporte") o 403 ES_TU_REPORTE
//     ("No puedes confirmar tu propio reporte"), muestra el mensaje y deja los botones deshabilitados.
// El servidor es quien decide (una respuesta por persona, no confirmar lo propio); esto solo evita mostrar lo que no sirve.
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ErrorApi } from '../api/cliente.ts'
import { confirmarReporte } from '../api/reportes.ts'
import type { ReportePublico, TipoConfirmacion } from '../api/tipos.ts'
import { useAuth } from '../context/AuthContexto.ts'
import { useReglas } from '../hooks/useReglas.ts'
import { mensajeErrorConfirmacion } from '../utils/errores.ts'
import { formatoFechaHora } from '../utils/fechas.ts'
import Alerta from './Alerta.tsx'
import Boton from './Boton.tsx'

interface Props {
  reporte: ReportePublico
  alActualizar: (reporte: ReportePublico) => void
}

interface Accion {
  tipo: TipoConfirmacion
  texto: string
  variante: 'primario' | 'secundario'
}

// Qué respuestas admite el reporte (contrato 6.5): `confirma` solo en baches abiertos; `sigue` y `ya_no_hay`
// solo en encharcamientos activos.
function accionesDe(reporte: ReportePublico): { pregunta: string; acciones: Accion[] } | null {
  if (reporte.categoria === 'encharcamiento' && reporte.estado === 'activo') {
    return {
      pregunta: '¿Sigue habiendo agua aquí?',
      acciones: [
        { tipo: 'sigue', texto: 'Sigue ahí', variante: 'primario' },
        { tipo: 'ya_no_hay', texto: 'Ya no hay agua', variante: 'secundario' },
      ],
    }
  }
  const bacheAbierto = ['recibido', 'validado', 'en_reparacion'].includes(reporte.estado)
  if (reporte.categoria === 'bache' && bacheAbierto) {
    return {
      pregunta: '¿Sigue el daño en este lugar?',
      acciones: [{ tipo: 'confirma', texto: 'Confirmar que sigue ahí', variante: 'primario' }],
    }
  }
  return null
}

export default function AccionesConfirmacion({ reporte, alActualizar }: Props) {
  const { usuario } = useAuth()
  const { vigencia_encharcamiento_horas } = useReglas()
  const ubicacion = useLocation()

  const [enviando, setEnviando] = useState<TipoConfirmacion | null>(null) // respuesta en curso
  const [bloqueado, setBloqueado] = useState(false) // ya respondió o es su reporte: los botones ya no sirven
  const [exito, setExito] = useState('')
  const [error, setError] = useState('')

  const opciones = accionesDe(reporte)
  // Si la respuesta cerró el reporte (tercer "Ya no hay agua") ya no hay botones, pero se conserva el mensaje de éxito
  if (!opciones) return exito ? <Alerta tipo="exito">{exito}</Alerta> : null

  // Sin sesión no se puede responder: se invita a entrar y se regresa a esta pantalla
  if (!usuario) {
    return (
      <p className="acciones-confirmacion">
        Para confirmar este reporte{' '}
        <Link to="/login" state={{ desde: ubicacion.pathname + ubicacion.search }}>
          inicia sesión
        </Link>
        .
      </p>
    )
  }

  // Moderadores y coordinadores no crean ni confirman reportes (contrato, sección 7)
  if (usuario.rol !== 'ciudadano') {
    return <p className="acciones-confirmacion">Solo las cuentas de ciudadano pueden confirmar reportes.</p>
  }

  async function responder(tipo: TipoConfirmacion) {
    setEnviando(tipo)
    setError('')
    setExito('')
    try {
      const actualizado = await confirmarReporte(reporte.id, tipo)
      setBloqueado(true)
      setExito(textoExito(tipo, vigencia_encharcamiento_horas))
      alActualizar(actualizado)
    } catch (e) {
      setError(mensajeErrorConfirmacion(e))
      // Estas dos respuestas no cambian si se vuelve a intentar
      if (e instanceof ErrorApi && (e.codigo === 'YA_CONFIRMADO' || e.codigo === 'ES_TU_REPORTE')) setBloqueado(true)
    } finally {
      setEnviando(null)
    }
  }

  return (
    <section className="acciones-confirmacion" aria-label="Confirmar este reporte">
      <h2>{opciones.pregunta}</h2>
      <div className="acciones-confirmacion-botones">
        {opciones.acciones.map((accion) => (
          <Boton
            key={accion.tipo}
            variante={accion.variante}
            onClick={() => void responder(accion.tipo)}
            disabled={bloqueado || enviando !== null}
            cargando={enviando === accion.tipo}
            textoCargando="Enviando…"
          >
            {accion.texto}
          </Boton>
        ))}
      </div>
      {exito && <Alerta tipo="exito">{exito}</Alerta>}
      {error && <Alerta tipo="error">{error}</Alerta>}
    </section>
  )
}

// Mensaje de éxito con la fecha y hora de la respuesta (hora de Ciudad Juárez, HU-03.3 CA1)
function textoExito(tipo: TipoConfirmacion, horasVigencia: number): string {
  const cuando = formatoFechaHora(new Date().toISOString())
  if (tipo === 'sigue') return `Gracias. Registramos que sigue ahí (${cuando}, hora de Ciudad Juárez). El reporte se mantiene vigente ${horasVigencia} horas más.`
  if (tipo === 'ya_no_hay') return `Gracias. Registramos que ya no hay agua (${cuando}, hora de Ciudad Juárez).`
  return `Gracias. Confirmaste este reporte (${cuando}, hora de Ciudad Juárez).`
}
