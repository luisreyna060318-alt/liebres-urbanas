// /reportar (solo ciudadano): primero se elige qué se reporta y después aparece el formulario de esa categoría.
// Al terminar se muestra ConfirmacionReporte con el folio (o el aviso de que se confirmó un reporte existente).
import { useState } from 'react'
import type { ReporteMio, ReportePublico } from '../api/tipos.ts'
import ConfirmacionReporte from '../componentes/ConfirmacionReporte.tsx'
import FormularioBache from '../componentes/FormularioBache.tsx'
import GrupoRadios from '../componentes/GrupoRadios.tsx'
import { useTitulo } from '../hooks/useTitulo.ts'

type Resultado = { modo: 'creado'; reporte: ReporteMio } | { modo: 'confirmado'; reporte: ReportePublico }

export default function Reportar() {
  useTitulo('Reportar un problema')
  const [categoria, setCategoria] = useState('')
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [intento, setIntento] = useState(0) // cambia la `key` del formulario para empezar uno limpio

  function reportarOtro() {
    setResultado(null)
    setCategoria('')
    setIntento((n) => n + 1)
  }

  if (resultado) {
    return <ConfirmacionReporte modo={resultado.modo} reporte={resultado.reporte} alReportarOtro={reportarOtro} />
  }

  return (
    <section>
      <h1>Reportar un problema</h1>
      <p>Cuéntanos qué viste y dónde. Los campos marcados con * son obligatorios.</p>

      <div className="formulario">
        <GrupoRadios
          id="categoria"
          leyenda="¿Qué quieres reportar?"
          opciones={[
            { valor: 'bache', etiqueta: 'Bache o daño en el pavimento' },
            // El encharcamiento se habilita en la rama que construye su formulario (HU-03.1)
            { valor: 'encharcamiento', etiqueta: 'Encharcamiento (Próximamente)', deshabilitada: true },
          ]}
          valor={categoria}
          onCambio={setCategoria}
          requerido
        />
      </div>

      {categoria === 'bache' && (
        <FormularioBache
          key={intento}
          alGuardar={(reporte) => setResultado({ modo: 'creado', reporte })}
          alConfirmar={(reporte) => setResultado({ modo: 'confirmado', reporte })}
        />
      )}
    </section>
  )
}
