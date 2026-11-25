// Formulario para reportar un bache o daño en el pavimento (HU-02.1, HU-02.2 y HU-02.3).
// Es dinámico: al elegir el tipo de daño aparecen solo los campos de ese tipo (ver CAMPOS_POR_TIPO en utils/reportes.ts).
//   <FormularioBache alCrear={(reporte) => ...} alConfirmar={(reporte) => ...} />
// - Valida en el cliente con las mismas reglas del servidor y muestra el mensaje junto a cada campo.
// - Si el envío falla (sin conexión, límite por hora, fuera del municipio...) NO se borra nada: todo vive en el estado.
// - Si el servidor responde 409 POSIBLE_DUPLICADO muestra DuplicadosAviso: confirmar el existente o reportar de todos modos.
import { useState } from 'react'
import type { FormEvent } from 'react'
import { pedirTiposDano } from '../api/catalogos.ts'
import { ErrorApi } from '../api/cliente.ts'
import { confirmarReporte, crearBache } from '../api/reportes.ts'
import type { ReporteCercano, ReporteMio, ReportePublico } from '../api/tipos.ts'
import { useApi } from '../hooks/useApi.ts'
import { useReglas } from '../hooks/useReglas.ts'
import { interpretarErrorEnvio, mensajeErrorConfirmacion } from '../utils/errores.ts'
import { ETIQUETA_CARRIL, ETIQUETA_PROFUNDIDAD, ETIQUETA_TAMANO, opcionesDe } from '../utils/etiquetas.ts'
import { armarBache, BACHE_VACIO, camposDeTipo, UBICACION_VACIA, validarBache } from '../utils/reportes.ts'
import type { DatosBache, DatosUbicacion, Errores } from '../utils/reportes.ts'
import Alerta from './Alerta.tsx'
import Boton from './Boton.tsx'
import Campo from './Campo.tsx'
import DuplicadosAviso from './DuplicadosAviso.tsx'
import Estado from './Estado.tsx'
import GrupoRadios from './GrupoRadios.tsx'
import SelectorUbicacion from './SelectorUbicacion.tsx'

interface Props {
  alCrear: (reporte: ReporteMio) => void // 201: se creó el reporte
  alConfirmar: (reporte: ReportePublico) => void // la persona confirmó uno existente en vez de crear otro
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

export default function FormularioBache({ alCrear, alConfirmar }: Props) {
  const reglas = useReglas()
  const tipos = useApi(() => pedirTiposDano())

  const [ubicacion, setUbicacion] = useState<DatosUbicacion>(UBICACION_VACIA)
  const [datos, setDatos] = useState<DatosBache>(BACHE_VACIO)
  const [errores, setErrores] = useState<Errores>({})
  const [errorEnvio, setErrorEnvio] = useState('')
  const [enviando, setEnviando] = useState(false)

  // Posibles duplicados que respondió el servidor (null = no hay aviso)
  const [duplicados, setDuplicados] = useState<ReporteCercano[] | null>(null)
  const [confirmandoId, setConfirmandoId] = useState<number | null>(null)
  const [errorConfirmacion, setErrorConfirmacion] = useState('')

  const camposVisibles = camposDeTipo(datos.tipo_dano_codigo)

  function cambiar<K extends keyof DatosBache>(campo: K, valor: DatosBache[K]) {
    setDatos((anterior) => ({ ...anterior, [campo]: valor }))
  }

  function mostrarErrores(nuevos: Errores) {
    setErrores(nuevos)
    const primero = ORDEN.find((campo) => nuevos[campo])
    // Los campos de ubicación pueden acabar de aparecer: se espera al siguiente ciclo para enfocar
    if (primero) setTimeout(() => document.getElementById(`campo-${primero}`)?.focus(), 0)
  }

  async function enviar(forzar: boolean) {
    setErrorEnvio('')
    setErrorConfirmacion('')

    // 1) Validar en el cliente. Lo capturado no se borra aunque haya errores.
    const nuevos = validarBache(ubicacion, datos, reglas.descripcion_max)
    if (Object.keys(nuevos).length > 0) {
      setDuplicados(null)
      mostrarErrores(nuevos)
      return
    }
    setErrores({})

    // 2) Mandar el reporte a la API
    setEnviando(true)
    try {
      const creado = await crearBache(armarBache(ubicacion, datos, forzar))
      alCrear(creado)
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

  // "Confirmar este reporte": suma una confirmación al bache existente y no crea folio nuevo
  async function confirmarExistente(reporte: ReporteCercano) {
    setConfirmandoId(reporte.id)
    setErrorConfirmacion('')
    try {
      alConfirmar(await confirmarReporte(reporte.id, 'confirma'))
    } catch (e) {
      setErrorConfirmacion(mensajeErrorConfirmacion(e))
    } finally {
      setConfirmandoId(null)
    }
  }

  function alEnviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    void enviar(false)
  }

  // Errores del servidor sobre campos que no están en pantalla (para no esconderlos)
  const visibles = new Set(['calle', 'colonia_id', 'lat', 'lon', 'tipo_dano_codigo', 'descripcion', ...camposVisibles])
  const erroresSinCampo = Object.entries(errores).filter(([campo]) => !visibles.has(campo))

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
      <form className="formulario formulario-reporte" onSubmit={alEnviar} noValidate aria-label="Reportar un bache">
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

        {erroresSinCampo.length > 0 && (
          <Alerta tipo="error">
            <ul className="lista-errores">
              {erroresSinCampo.map(([campo, mensaje]) => (
                <li key={campo}>{mensaje}</li>
              ))}
            </ul>
          </Alerta>
        )}
        {errorEnvio && <Alerta tipo="error">{errorEnvio}</Alerta>}

        {duplicados ? (
          <DuplicadosAviso
            duplicados={duplicados}
            textoConfirmar="Confirmar este reporte"
            textoForzar="Es un daño distinto, reportarlo de todos modos"
            alConfirmar={confirmarExistente}
            alForzar={() => {
              setDuplicados(null)
              void enviar(true)
            }}
            alVolver={() => setDuplicados(null)}
            ocupado={enviando || confirmandoId !== null}
            confirmandoId={confirmandoId}
            error={errorConfirmacion}
          />
        ) : (
          <Boton type="submit" cargando={enviando} textoCargando="Enviando reporte…">
            Enviar reporte
          </Boton>
        )}
      </form>
    </Estado>
  )
}
