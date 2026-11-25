// Aviso de posible duplicado (HU-02.3 y HU-03.1 CA4): el servidor encontró reportes abiertos cerca del punto.
// Muestra cada uno con TarjetaReporte y deja elegir entre confirmar el existente (sin folio nuevo) o reportar de todos modos.
// No llama a la API: quien lo usa pasa las acciones (confirmar con POST .../confirmaciones, o reenviar con forzar: true).
import type { ReporteCercano } from '../api/tipos.ts'
import Alerta from './Alerta.tsx'
import Boton from './Boton.tsx'
import TarjetaReporte from './TarjetaReporte.tsx'

interface Props {
  duplicados: ReporteCercano[]
  // Textos según la categoría: baches ("Confirmar este reporte") o encharcamientos ("Sigue ahí")
  textoConfirmar: string
  textoForzar: string
  alConfirmar: (reporte: ReporteCercano) => void
  alForzar: () => void
  alVolver: () => void // regresa a editar los datos sin enviar nada
  ocupado?: boolean // hay una petición en curso: se deshabilitan los botones
  confirmandoId?: number | null // reporte que se está confirmando (para el texto "Confirmando…")
  error?: string
}

export default function DuplicadosAviso({
  duplicados,
  textoConfirmar,
  textoForzar,
  alConfirmar,
  alForzar,
  alVolver,
  ocupado = false,
  confirmandoId = null,
  error,
}: Props) {
  const plural = duplicados.length > 1

  return (
    <section className="duplicados" aria-labelledby="duplicados-titulo">
      <h2 id="duplicados-titulo">¿Es el mismo problema?</h2>
      <Alerta tipo="aviso">
        {plural
          ? 'Ya hay reportes abiertos muy cerca de este punto.'
          : 'Ya hay un reporte abierto muy cerca de este punto.'}{' '}
        Si es el mismo, confírmalo: así cuenta tu aviso sin crear un folio nuevo.
      </Alerta>

      <ul className="duplicados-lista">
        {duplicados.map((d) => (
          <li key={d.id}>
            <TarjetaReporte
              reporte={d}
              acciones={
                <Boton
                  onClick={() => alConfirmar(d)}
                  disabled={ocupado}
                  cargando={confirmandoId === d.id}
                  textoCargando="Confirmando…"
                >
                  {textoConfirmar}
                  {/* El folio ayuda a distinguir los botones cuando hay varios reportes */}
                  <span className="solo-lectores"> {d.folio}</span>
                </Boton>
              }
            />
          </li>
        ))}
      </ul>

      {error && <Alerta tipo="error">{error}</Alerta>}

      <div className="duplicados-acciones">
        <Boton variante="secundario" onClick={alForzar} disabled={ocupado}>
          {textoForzar}
        </Boton>
        <Boton variante="secundario" onClick={alVolver} disabled={ocupado}>
          Volver a mis datos
        </Boton>
      </div>
    </section>
  )
}
