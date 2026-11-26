// /reportes/:id (pública, HU-04.4): folio, tipo, ubicación, datos del daño, confirmaciones, estado y el historial
// del más reciente al más antiguo. En los baches, además, la fecha del reporte, la longevidad y la última confirmación.
// Todas las fechas se muestran en la hora de Ciudad Juárez. El historial público no dice quién hizo cada cambio.
import { useState } from 'react'
import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ErrorApi } from '../api/cliente.ts'
import { pedirDetalle } from '../api/reportes.ts'
import type { CambioEstado, ReporteDetalle, ReportePublico } from '../api/tipos.ts'
import AccionesConfirmacion from '../componentes/AccionesConfirmacion.tsx'
import Estado from '../componentes/Estado.tsx'
import { useAuth } from '../context/AuthContexto.ts'
import { useApi } from '../hooks/useApi.ts'
import { useTitulo } from '../hooks/useTitulo.ts'
import { formatoFecha, formatoFechaHora } from '../utils/fechas.ts'
import {
  ETIQUETA_CARRIL,
  ETIQUETA_CATEGORIA,
  ETIQUETA_ESTADO,
  ETIQUETA_NIVEL_AGUA,
  ETIQUETA_PROFUNDIDAD,
  ETIQUETA_SEVERIDAD,
  ETIQUETA_TAMANO,
  ICONO_CATEGORIA,
} from '../utils/etiquetas.ts'
import { ROLES_MODERADOR } from '../utils/menu.ts'
import RechazarEncharcamiento from './moderacion/RechazarEncharcamiento.tsx'

// Un 404 no es una falla: el reporte no existe (o está rechazado). Se devuelve null para mostrar un mensaje amable.
async function pedirOMarcarAusente(id: number): Promise<ReporteDetalle | null> {
  try {
    return await pedirDetalle(id)
  } catch (e) {
    if (e instanceof ErrorApi && e.status === 404) return null
    throw e
  }
}

const textoDias = (dias: number) => `${dias} ${dias === 1 ? 'día' : 'días'}`
const siNo = (valor: boolean | null) => (valor === null ? 'Sin dato' : valor ? 'Sí' : 'No')

export default function DetalleReporte() {
  const { id } = useParams()
  const idNumero = /^\d+$/.test(id ?? '') ? Number(id) : null
  const detalle = useApi(() => (idNumero === null ? Promise.resolve(null) : pedirOMarcarAusente(idNumero)), [idNumero])
  const reporte = detalle.datos
  useTitulo(reporte ? `Reporte ${reporte.folio}` : 'Detalle del reporte')

  const noExiste = !detalle.cargando && !detalle.error && reporte === null

  return (
    <section>
      <h1>{reporte ? `Reporte ${reporte.folio}` : 'Detalle del reporte'}</h1>

      <Estado cargando={detalle.cargando} error={detalle.error} textoCargando="Cargando el reporte…" onReintentar={detalle.recargar}>
        {noExiste && (
          <div className="estado" role="status">
            <p>Este reporte no existe o ya no está disponible.</p>
          </div>
        )}
        {reporte && <Contenido reporte={reporte} />}
      </Estado>

      <p className="enlace-aparte">
        <Link to="/">Volver a los reportes</Link>
      </p>
    </section>
  )
}

function Contenido({ reporte }: { reporte: ReporteDetalle }) {
  const [r, setReporte] = useState(reporte)
  const { tienePermiso } = useAuth()
  const esBache = r.categoria === 'bache'

  // Después de confirmar o desmentir se muestran los datos que respondió el servidor y se vuelve a pedir el detalle
  // (historial y fecha de la última confirmación) sin quitar la pantalla, para no perder el mensaje de éxito.
  async function alActualizar(actualizado: ReportePublico) {
    setReporte((anterior) => ({ ...anterior, ...actualizado }))
    await refrescar()
  }

  async function refrescar() {
    try {
      setReporte(await pedirDetalle(reporte.id))
    } catch {
      // Si falla, quedan en pantalla los datos que ya se tenían
    }
  }

  return (
    <>
      <p className="tarjeta-reporte-tipo">
        <span aria-hidden="true">{ICONO_CATEGORIA[r.categoria]} </span>
        {ETIQUETA_CATEGORIA[r.categoria]}
        {r.sin_validar && <span className="etiqueta-aparte"> (Sin validar)</span>}
      </p>
      <p className="etiqueta-estado">Estado: {ETIQUETA_ESTADO[r.estado]}</p>

      <h2>Datos del reporte</h2>
      <dl className="datos-reporte">
        <Dato termino="Ubicación">
          {r.calle}, {r.colonia.nombre}
        </Dato>
        <Dato termino="Coordenadas">
          {r.lat.toFixed(5)}, {r.lon.toFixed(5)}
        </Dato>
        {esBache ? (
          <>
            {r.tipo_dano && <Dato termino="Tipo de daño">{r.tipo_dano.nombre}</Dato>}
            {r.tamano && <Dato termino="Tamaño">{ETIQUETA_TAMANO[r.tamano]}</Dato>}
            {r.profundidad && <Dato termino="Profundidad">{ETIQUETA_PROFUNDIDAD[r.profundidad]}</Dato>}
            {r.carril && <Dato termino="Carril">{ETIQUETA_CARRIL[r.carril]}</Dato>}
            {r.tipo_dano?.codigo === 'alcantarilla_sin_tapa' && <Dato termino="¿Señalizada?">{siNo(r.senalizado)}</Dato>}
            {r.severidad && <Dato termino="Severidad">{ETIQUETA_SEVERIDAD[r.severidad]}</Dato>}
          </>
        ) : (
          <>
            {r.nivel_agua && <Dato termino="Nivel del agua">{ETIQUETA_NIVEL_AGUA[r.nivel_agua]}</Dato>}
            {r.nivel_agua === 'intransitable' && <Dato termino="¿Personas o vehículos en riesgo?">{siNo(r.hay_riesgo)}</Dato>}
            {r.estado === 'activo' && <Dato termino="Vigente hasta">{formatoFechaHora(r.vigente_hasta)}</Dato>}
          </>
        )}
        {r.descripcion && <Dato termino="Descripción">{r.descripcion}</Dato>}
        <Dato termino="Confirmaciones">{r.confirmaciones}</Dato>
        <Dato termino="Reportado el">{formatoFechaHora(r.creado_en)}</Dato>
        {esBache && (
          <>
            <Dato termino="Longevidad">
              {textoDias(r.longevidad_dias)}
              {r.estado === 'reparado' ? ' (hasta su reparación)' : ' sin reparar'}
            </Dato>
            {r.fecha_reparacion && <Dato termino="Reparado el">{formatoFecha(r.fecha_reparacion)}</Dato>}
            <Dato termino="Última confirmación">
              {r.ultima_confirmacion ? formatoFechaHora(r.ultima_confirmacion) : 'Nadie lo ha confirmado todavía'}
            </Dato>
          </>
        )}
      </dl>

      {/* HU-03.3 y HU-02.3: "Sigue ahí", "Ya no hay agua" o confirmar un bache abierto */}
      <AccionesConfirmacion reporte={r} alActualizar={(actualizado) => void alActualizar(actualizado)} />

      {!esBache && tienePermiso(ROLES_MODERADOR) && <RechazarEncharcamiento reporte={r} alCambiar={() => void refrescar()} />}

      <h2>Historial</h2>
      {r.historial.length === 0 ? (
        <p>Todavía no hay cambios registrados.</p>
      ) : (
        <ol className="historial-reporte">
          {r.historial.map((cambio, i) => (
            <li key={`${cambio.creado_en}-${i}`}>
              <Cambio cambio={cambio} />
            </li>
          ))}
        </ol>
      )}
    </>
  )
}

function Dato({ termino, children }: { termino: string; children: ReactNode }) {
  return (
    <div>
      <dt>{termino}</dt>
      <dd>{children}</dd>
    </div>
  )
}

function Cambio({ cambio }: { cambio: CambioEstado }) {
  return (
    <>
      <p>
        <time dateTime={cambio.creado_en}>{formatoFechaHora(cambio.creado_en)}</time>
        {' · '}
        <strong>
          {cambio.estado_anterior
            ? `Pasó de ${ETIQUETA_ESTADO[cambio.estado_anterior]} a ${ETIQUETA_ESTADO[cambio.estado_nuevo]}`
            : `Se reportó como ${ETIQUETA_ESTADO[cambio.estado_nuevo]}`}
        </strong>
      </p>
      {cambio.comentario && <p className="historial-comentario">{cambio.comentario}</p>}
    </>
  )
}
