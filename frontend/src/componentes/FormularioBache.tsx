// Formulario para reportar un bache o daño en el pavimento (HU-02.1, HU-02.2 y HU-02.3) y para corregirlo (HU-02.5).
// Es dinámico: al elegir el tipo de daño aparecen solo los campos de ese tipo (ver CAMPOS_POR_TIPO en utils/reportes.ts).
//   Crear:  <FormularioBache alGuardar={(reporte) => ...} alConfirmar={(reporte) => ...} />
//   Editar: <FormularioBache reporte={reporteExistente} alGuardar={(reporte) => ...} />   (usa PUT, sin duplicados)
// - Valida en el cliente con las mismas reglas del servidor y muestra el mensaje junto a cada campo.
// - Si el envío falla (sin conexión, límite por hora, fuera del municipio...) NO se borra nada: todo vive en el estado.
// - Si el servidor responde 409 POSIBLE_DUPLICADO muestra DuplicadosAviso: confirmar el existente o reportar de todos modos.
//   Esa parte del envío es la misma para encharcamientos y vive en useEnvioReporte.
import { useState } from 'react'
import type { FormEvent } from 'react'
import { pedirTiposDano } from '../api/catalogos.ts'
import { crearBache, editarReporte } from '../api/reportes.ts'
import type { ReporteMio, ReportePublico } from '../api/tipos.ts'
import { useApi } from '../hooks/useApi.ts'
import { useEnvioReporte } from '../hooks/useEnvioReporte.ts'
import { useReglas } from '../hooks/useReglas.ts'
import { ETIQUETA_CARRIL, ETIQUETA_PROFUNDIDAD, ETIQUETA_TAMANO, opcionesDe } from '../utils/etiquetas.ts'
import {
  armarBache,
  armarCamposBache,
  BACHE_VACIO,
  bacheDeReporte,
  camposDeTipo,
  UBICACION_VACIA,
  ubicacionDeReporte,
  validarBache,
} from '../utils/reportes.ts'
import type { DatosBache, DatosUbicacion } from '../utils/reportes.ts'
import Alerta from './Alerta.tsx'
import Campo from './Campo.tsx'
import Estado from './Estado.tsx'
import GrupoRadios from './GrupoRadios.tsx'
import PieFormularioReporte from './PieFormularioReporte.tsx'
import SelectorUbicacion from './SelectorUbicacion.tsx'

interface Props {
  reporte?: ReportePublico // si se pasa, el formulario edita ese reporte (PUT) en vez de crear uno nuevo
  alGuardar: (reporte: ReporteMio) => void // se creó (201) o se guardaron los cambios (200)
  alConfirmar?: (reporte: ReportePublico) => void // al crear: la persona confirmó uno existente en vez de crear otro
}

// Orden en que aparecen los campos en pantalla: el foco va al primero que tenga error
const ORDEN = [
  'calle',
  'colonia_id',
  'lat',
  'lon',
  'tipo_dano_codigo',
  'tamano',
  'profundidad',
  'carril',
  'senalizado',
  'descripcion',
]

export default function FormularioBache({ reporte, alGuardar, alConfirmar }: Props) {
  const editando = reporte !== undefined
  const reglas = useReglas()
  const tipos = useApi(() => pedirTiposDano())

  const [ubicacion, setUbicacion] = useState<DatosUbicacion>(reporte ? ubicacionDeReporte(reporte) : UBICACION_VACIA)
  const [datos, setDatos] = useState<DatosBache>(reporte ? bacheDeReporte(reporte) : BACHE_VACIO)

  const envio = useEnvioReporte({
    validar: () => validarBache(ubicacion, datos, reglas.descripcion_max),
    crear: (forzar) =>
      reporte
        ? editarReporte(reporte.id, armarCamposBache(ubicacion, datos))
        : crearBache(armarBache(ubicacion, datos, forzar)),
    tipoConfirmacion: 'confirma',
    ordenCampos: ORDEN,
    alGuardar,
    alConfirmar,
  })
  const { errores } = envio

  const camposVisibles = camposDeTipo(datos.tipo_dano_codigo)

  function cambiar<K extends keyof DatosBache>(campo: K, valor: DatosBache[K]) {
    setDatos((anterior) => ({ ...anterior, [campo]: valor }))
  }

  function alEnviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    void envio.enviar()
  }

  // Errores del servidor sobre campos que no están en pantalla (para no esconderlos)
  const visibles = new Set(['calle', 'colonia_id', 'lat', 'lon', 'tipo_dano_codigo', 'descripcion', ...camposVisibles])
  const erroresSinCampo = Object.entries(errores)
    .filter(([campo]) => !visibles.has(campo))
    .map(([, mensaje]) => mensaje)

  const restantes = reglas.descripcion_max - datos.descripcion.length

  return (
    <Estado
      cargando={tipos.cargando}
      error={tipos.error}
      vacio={tipos.datos?.length === 0}
      textoCargando="Cargando el formulario…"
      textoVacio="Por ahora no hay tipos de daño disponibles. Inténtalo más tarde."
      onReintentar={tipos.recargar}
    >
      {/* noValidate: los mensajes los muestra nuestra validación, no el navegador */}
      <form
        className="formulario formulario-reporte"
        onSubmit={alEnviar}
        noValidate
        aria-label={editando ? 'Editar el reporte' : 'Reportar un bache'}
      >
        <SelectorUbicacion valor={ubicacion} onCambio={setUbicacion} errores={errores} />

        <fieldset className="grupo-dano">
          <legend>Qué daño es</legend>

          <Campo
            id="campo-tipo_dano_codigo"
            etiqueta="Tipo de daño"
            tipo="select"
            textoOpcionVacia="Elige el tipo de daño…"
            opciones={(tipos.datos ?? []).map((t) => ({ valor: t.codigo, etiqueta: t.nombre }))}
            valor={datos.tipo_dano_codigo}
            onCambio={(v) => cambiar('tipo_dano_codigo', v as DatosBache['tipo_dano_codigo'])}
            error={errores.tipo_dano_codigo}
            requerido
          />

          {/* Solo aparecen los campos del tipo elegido */}
          {camposVisibles.includes('tamano') && (
            <Campo
              id="campo-tamano"
              etiqueta="Tamaño"
              tipo="select"
              opciones={opcionesDe(ETIQUETA_TAMANO)}
              valor={datos.tamano}
              onCambio={(v) => cambiar('tamano', v as DatosBache['tamano'])}
              error={errores.tamano}
              requerido
            />
          )}
          {camposVisibles.includes('profundidad') && (
            <Campo
              id="campo-profundidad"
              etiqueta="Profundidad"
              tipo="select"
              opciones={opcionesDe(ETIQUETA_PROFUNDIDAD)}
              valor={datos.profundidad}
              onCambio={(v) => cambiar('profundidad', v as DatosBache['profundidad'])}
              error={errores.profundidad}
              requerido
            />
          )}
          {camposVisibles.includes('carril') && (
            <Campo
              id="campo-carril"
              etiqueta="Carril afectado"
              tipo="select"
              opciones={opcionesDe(ETIQUETA_CARRIL)}
              valor={datos.carril}
              onCambio={(v) => cambiar('carril', v as DatosBache['carril'])}
              error={errores.carril}
              requerido
            />
          )}
          {camposVisibles.includes('senalizado') && (
            <>
              <GrupoRadios
                id="campo-senalizado"
                leyenda="¿El punto está señalizado?"
                ayuda="Por ejemplo con conos, cinta o una señal de advertencia."
                opciones={[
                  { valor: 'si', etiqueta: 'Sí, está señalizado' },
                  { valor: 'no', etiqueta: 'No, no está señalizado' },
                ]}
                valor={datos.senalizado}
                onCambio={(v) => cambiar('senalizado', v as DatosBache['senalizado'])}
                error={errores.senalizado}
                requerido
              />
              <Alerta tipo="aviso">Una alcantarilla sin tapa es peligrosa: su severidad será Alta automáticamente.</Alerta>
            </>
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
          textoEnviar={editando ? 'Guardar cambios' : 'Enviar reporte'}
          textoEnviando={editando ? 'Guardando cambios…' : 'Enviando reporte…'}
          textoConfirmar="Confirmar este reporte"
          textoForzar="Es un daño distinto, reportarlo de todos modos"
          erroresSinCampo={erroresSinCampo}
        />
      </form>
    </Estado>
  )
}
