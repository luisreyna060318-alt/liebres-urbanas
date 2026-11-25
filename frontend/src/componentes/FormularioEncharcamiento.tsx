// Formulario para reportar un encharcamiento (HU-03.1): ubicación, nivel del agua y descripción opcional.
//   <FormularioEncharcamiento alGuardar={(reporte) => ...} alConfirmar={(reporte) => ...} />
// Si el nivel es "Intransitable" aparece la pregunta obligatoria "¿hay vehículos varados o personas en riesgo?".
// El envío (validación, errores, duplicados) es el mismo de FormularioBache y vive en useEnvioReporte; aquí un duplicado
// se resuelve con "Sigue ahí" (confirma el encharcamiento existente) o "Reportarlo de todos modos".
import { useState } from 'react'
import type { FormEvent } from 'react'
import { crearEncharcamiento } from '../api/reportes.ts'
import type { ReporteMio, ReportePublico } from '../api/tipos.ts'
import { useEnvioReporte } from '../hooks/useEnvioReporte.ts'
import { useReglas } from '../hooks/useReglas.ts'
import { ETIQUETA_NIVEL_AGUA } from '../utils/etiquetas.ts'
import {
  armarEncharcamiento,
  ENCHARCAMIENTO_VACIO,
  preguntaRiesgoVisible,
  UBICACION_VACIA,
  validarEncharcamiento,
} from '../utils/reportes.ts'
import type { DatosEncharcamiento, DatosUbicacion } from '../utils/reportes.ts'
import Campo from './Campo.tsx'
import GrupoRadios from './GrupoRadios.tsx'
import PieFormularioReporte from './PieFormularioReporte.tsx'
import SelectorUbicacion from './SelectorUbicacion.tsx'

interface Props {
  alGuardar: (reporte: ReporteMio) => void // 201: se creó el reporte (queda Activo de inmediato)
  alConfirmar: (reporte: ReportePublico) => void // la persona confirmó uno existente en vez de crear otro
}

// Orden en que aparecen los campos en pantalla: el foco va al primero que tenga error
const ORDEN = ['calle', 'colonia_id', 'lat', 'lon', 'nivel_agua', 'hay_riesgo', 'descripcion']

const NIVELES = (Object.keys(ETIQUETA_NIVEL_AGUA) as (keyof typeof ETIQUETA_NIVEL_AGUA)[]).map((valor) => ({
  valor,
  etiqueta: ETIQUETA_NIVEL_AGUA[valor],
}))

export default function FormularioEncharcamiento({ alGuardar, alConfirmar }: Props) {
  const reglas = useReglas()
  const [ubicacion, setUbicacion] = useState<DatosUbicacion>(UBICACION_VACIA)
  const [datos, setDatos] = useState<DatosEncharcamiento>(ENCHARCAMIENTO_VACIO)

  const envio = useEnvioReporte({
    validar: () => validarEncharcamiento(ubicacion, datos, reglas.descripcion_max),
    crear: (forzar) => crearEncharcamiento(armarEncharcamiento(ubicacion, datos, forzar)),
    tipoConfirmacion: 'sigue',
    ordenCampos: ORDEN,
    alGuardar,
    alConfirmar,
  })
  const { errores } = envio

  function cambiar<K extends keyof DatosEncharcamiento>(campo: K, valor: DatosEncharcamiento[K]) {
    setDatos((anterior) => ({ ...anterior, [campo]: valor }))
  }

  function alEnviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    void envio.enviar()
  }

  const visibles = new Set(['calle', 'colonia_id', 'lat', 'lon', 'nivel_agua', 'descripcion'])
  if (preguntaRiesgoVisible(datos)) visibles.add('hay_riesgo')
  const erroresSinCampo = Object.entries(errores)
    .filter(([campo]) => !visibles.has(campo))
    .map(([, mensaje]) => mensaje)

  const restantes = reglas.descripcion_max - datos.descripcion.length

  return (
    <form className="formulario formulario-reporte" onSubmit={alEnviar} noValidate aria-label="Reportar un encharcamiento">
      <SelectorUbicacion valor={ubicacion} onCambio={setUbicacion} errores={errores} />

      <fieldset className="grupo-dano">
        <legend>Cuánta agua hay</legend>

        <GrupoRadios
          id="campo-nivel_agua"
          leyenda="Nivel del agua"
          opciones={NIVELES}
          valor={datos.nivel_agua}
          onCambio={(v) => cambiar('nivel_agua', v as DatosEncharcamiento['nivel_agua'])}
          error={errores.nivel_agua}
          requerido
        />

        {preguntaRiesgoVisible(datos) && (
          <GrupoRadios
            id="campo-hay_riesgo"
            leyenda="¿Hay vehículos varados o personas en riesgo?"
            ayuda="Si hay una emergencia, llama al 911."
            opciones={[
              { valor: 'si', etiqueta: 'Sí, hay vehículos varados o personas en riesgo' },
              { valor: 'no', etiqueta: 'No' },
            ]}
            valor={datos.hay_riesgo}
            onCambio={(v) => cambiar('hay_riesgo', v as DatosEncharcamiento['hay_riesgo'])}
            error={errores.hay_riesgo}
            requerido
          />
        )}
      </fieldset>

      <Campo
        id="campo-descripcion"
        etiqueta="Descripción (opcional)"
        tipo="textarea"
        valor={datos.descripcion}
        onCambio={(v) => cambiar('descripcion', v)}
        maxLength={reglas.descripcion_max}
        ayuda={`${datos.descripcion.length} de ${reglas.descripcion_max} caracteres (${restantes} disponibles).`}
        error={errores.descripcion}
      />

      <PieFormularioReporte
        envio={envio}
        textoEnviar="Enviar reporte"
        textoEnviando="Enviando reporte…"
        textoConfirmar="Sigue ahí"
        textoForzar="Reportarlo de todos modos"
        erroresSinCampo={erroresSinCampo}
      />
    </form>
  )
}
