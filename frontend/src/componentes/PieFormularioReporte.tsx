// Parte final de los formularios de reporte: errores del servidor, aviso de duplicados y botón de enviar.
// La comparten FormularioBache y FormularioEncharcamiento; el estado viene de useEnvioReporte.
import type { EnvioReporte } from '../hooks/useEnvioReporte.ts'
import Alerta from './Alerta.tsx'
import Boton from './Boton.tsx'
import DuplicadosAviso from './DuplicadosAviso.tsx'

interface Props {
  envio: EnvioReporte
  textoEnviar: string
  textoEnviando: string
  textoConfirmar: string // acción sobre un duplicado: "Confirmar este reporte" o "Sigue ahí"
  textoForzar: string
  erroresSinCampo: string[] // errores del servidor sobre campos que no están en pantalla (para no esconderlos)
}

export default function PieFormularioReporte({
  envio,
  textoEnviar,
  textoEnviando,
  textoConfirmar,
  textoForzar,
  erroresSinCampo,
}: Props) {
  return (
    <>
      {erroresSinCampo.length > 0 && (
        <Alerta tipo="error">
          <ul className="lista-errores">
            {erroresSinCampo.map((mensaje) => (
              <li key={mensaje}>{mensaje}</li>
            ))}
          </ul>
        </Alerta>
      )}
      {envio.errorEnvio && <Alerta tipo="error">{envio.errorEnvio}</Alerta>}

      {envio.duplicados ? (
        <DuplicadosAviso
          duplicados={envio.duplicados}
          textoConfirmar={textoConfirmar}
          textoForzar={textoForzar}
          alConfirmar={envio.confirmarExistente}
          alForzar={() => {
            envio.cerrarDuplicados()
            void envio.enviar(true)
          }}
          alVolver={envio.cerrarDuplicados}
          ocupado={envio.enviando || envio.confirmandoId !== null}
          confirmandoId={envio.confirmandoId}
          error={envio.errorConfirmacion}
        />
      ) : (
        <Boton type="submit" cargando={envio.enviando} textoCargando={textoEnviando}>
          {textoEnviar}
        </Boton>
      )}
    </>
  )
}
