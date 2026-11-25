import { useState } from 'react'
import { ErrorApi } from '../api/cliente.ts'
import { confirmarReporte } from '../api/reportes.ts'
import type { ReporteCercano, ReporteMio, ReportePublico, TipoConfirmacion } from '../api/tipos.ts'
import { interpretarErrorEnvio, mensajeErrorConfirmacion } from '../utils/errores.ts'
import type { Errores } from '../utils/reportes.ts'
import { useReglas } from './useReglas.ts'

// Lo que cambia entre un formulario y otro (bache o encharcamiento); el resto del envío es igual.
interface Opciones {
  validar: () => Errores // errores del cliente; vacío = se puede enviar
  crear: (forzar: boolean) => Promise<ReporteMio> // llama a la API (POST o PUT)
  tipoConfirmacion: TipoConfirmacion // 'confirma' (bache) o 'sigue' (encharcamiento) cuando se elige confirmar un duplicado
  ordenCampos: string[] // orden de los campos en pantalla: el foco va al primero con error
  alGuardar: (reporte: ReporteMio) => void
  alConfirmar?: (reporte: ReportePublico) => void
}

// Lógica de envío que comparten FormularioBache y FormularioEncharcamiento (HU-02.1, HU-02.3, HU-03.1):
// validar, enviar, y reaccionar a los errores del contrato. Si algo falla NO se toca lo capturado, porque los datos
// viven en el estado del formulario y este hook solo guarda los mensajes y los duplicados.
export function useEnvioReporte({ validar, crear, tipoConfirmacion, ordenCampos, alGuardar, alConfirmar }: Opciones) {
  const reglas = useReglas()
  const [errores, setErrores] = useState<Errores>({})
  const [errorEnvio, setErrorEnvio] = useState('')
  const [enviando, setEnviando] = useState(false)

  // Posibles duplicados que respondió el servidor (null = no hay aviso)
  const [duplicados, setDuplicados] = useState<ReporteCercano[] | null>(null)
  const [confirmandoId, setConfirmandoId] = useState<number | null>(null)
  const [errorConfirmacion, setErrorConfirmacion] = useState('')

  function mostrarErrores(nuevos: Errores) {
    setErrores(nuevos)
    const primero = ordenCampos.find((campo) => nuevos[campo])
    // Los campos de ubicación pueden acabar de aparecer: se espera al siguiente ciclo para enfocar
    if (primero) setTimeout(() => document.getElementById(`campo-${primero}`)?.focus(), 0)
  }

  // forzar = true: "reportarlo de todos modos" después de un aviso de duplicado
  async function enviar(forzar = false) {
    setErrorEnvio('')
    setErrorConfirmacion('')

    // 1) Validar en el cliente
    const nuevos = validar()
    if (Object.keys(nuevos).length > 0) {
      setDuplicados(null)
      mostrarErrores(nuevos)
      return
    }
    setErrores({})

    // 2) Mandar a la API
    setEnviando(true)
    try {
      alGuardar(await crear(forzar))
    } catch (e) {
      if (e instanceof ErrorApi && e.codigo === 'POSIBLE_DUPLICADO' && e.duplicados.length > 0) {
        setDuplicados(e.duplicados)
        return
      }
      const { mensaje, campos } = interpretarErrorEnvio(e, reglas.max_reportes_por_hora)
      setDuplicados(null)
      setErrorEnvio(mensaje)
      if (Object.keys(campos).length > 0) mostrarErrores(campos)
    } finally {
      setEnviando(false)
    }
  }

  // Confirmar el reporte existente en lugar de crear uno nuevo: no se genera folio
  async function confirmarExistente(existente: ReporteCercano) {
    setConfirmandoId(existente.id)
    setErrorConfirmacion('')
    try {
      alConfirmar?.(await confirmarReporte(existente.id, tipoConfirmacion))
    } catch (e) {
      setErrorConfirmacion(mensajeErrorConfirmacion(e))
    } finally {
      setConfirmandoId(null)
    }
  }

  return {
    errores,
    errorEnvio,
    enviando,
    duplicados,
    confirmandoId,
    errorConfirmacion,
    enviar,
    confirmarExistente,
    cerrarDuplicados: () => setDuplicados(null),
  }
}

export type EnvioReporte = ReturnType<typeof useEnvioReporte>
