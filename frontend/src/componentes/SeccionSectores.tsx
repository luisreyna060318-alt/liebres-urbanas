// Sectores (HU-06.1): lista sencilla con un formulario para crear uno o renombrar el elegido.
import { useState } from 'react'
import { crearSector, renombrarSector } from '../api/catalogos.ts'
import { ErrorApi } from '../api/cliente.ts'
import type { Sector } from '../api/tipos.ts'
import Alerta from './Alerta.tsx'
import Boton from './Boton.tsx'
import Campo from './Campo.tsx'

const NOMBRE_SECTOR_MIN = 2
const NOMBRE_SECTOR_MAX = 80

interface Props {
  sectores: Sector[]
  alCambiar: (mensaje: string) => void // se llama después de crear o renombrar, para refrescar y avisar
}

export default function SeccionSectores({ sectores, alCambiar }: Props) {
  const [editando, setEditando] = useState<Sector | null>(null) // null = se está creando uno nuevo
  const [nombre, setNombre] = useState('')
  const [error, setError] = useState('')
  const [errorGeneral, setErrorGeneral] = useState('')
  const [enviando, setEnviando] = useState(false)

  function elegir(sector: Sector | null) {
    setEditando(sector)
    setNombre(sector?.nombre ?? '')
    setError('')
    setErrorGeneral('')
  }

  async function enviar(e: React.SyntheticEvent) {
    e.preventDefault()
    const limpio = nombre.trim()
    setErrorGeneral('')
    if (limpio.length < NOMBRE_SECTOR_MIN || limpio.length > NOMBRE_SECTOR_MAX) {
      setError(`El nombre debe tener entre ${NOMBRE_SECTOR_MIN} y ${NOMBRE_SECTOR_MAX} caracteres.`)
      return
    }
    setError('')
    setEnviando(true)
    try {
      const guardado = editando
        ? await renombrarSector(editando.id, { nombre: limpio })
        : await crearSector({ nombre: limpio })
      alCambiar(editando ? `Se renombró el sector a ${guardado.nombre}.` : `Se creó el sector ${guardado.nombre}.`)
      elegir(null)
    } catch (e) {
      if (e instanceof ErrorApi && e.campos.nombre) setError(e.campos.nombre)
      else setErrorGeneral(e instanceof Error ? e.message : 'No se pudo guardar el sector.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="admin-sectores" aria-labelledby="titulo-sectores">
      <h2 id="titulo-sectores">Sectores</h2>
      <ul className="admin-sectores-lista">
        {sectores.map((s) => (
          <li key={s.id}>
            <span>{s.nombre}</span>
            <Boton variante="secundario" onClick={() => elegir(s)}>
              Renombrar <span className="solo-lectores">{s.nombre}</span>
            </Boton>
          </li>
        ))}
      </ul>
      <form className="formulario formulario-admin" onSubmit={(e) => void enviar(e)} noValidate>
        <Campo
          id="sector-nombre"
          etiqueta={editando ? `Nuevo nombre del sector ${editando.nombre}` : 'Nombre del sector nuevo'}
          valor={nombre}
          onCambio={setNombre}
          error={error}
          maxLength={NOMBRE_SECTOR_MAX}
          requerido
        />
        {errorGeneral && <Alerta tipo="error">{errorGeneral}</Alerta>}
        <div className="formulario-admin-botones">
          <Boton type="submit" cargando={enviando} textoCargando="Guardando…">
            {editando ? 'Guardar nombre' : 'Crear sector'}
          </Boton>
          {editando && (
            <Boton variante="secundario" onClick={() => elegir(null)} disabled={enviando}>
              Cancelar
            </Boton>
          )}
        </div>
      </form>
    </section>
  )
}
