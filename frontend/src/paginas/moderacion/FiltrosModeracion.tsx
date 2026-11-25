// Filtros por colonia y tipo de daño de las listas de moderación. Al cambiar uno se vuelve a pedir la página 1.
import type { Colonia, TipoDano } from '../../api/tipos.ts'
import Campo from '../../componentes/Campo.tsx'

export interface Filtros {
  colonia_id: string // "" = todas
  tipo_dano_codigo: string // "" = todos
}

interface Props {
  idBase: string // para que los ids no se repitan si hay dos listas en la página
  filtros: Filtros
  onCambiar: (filtros: Filtros) => void
  colonias: Colonia[]
  tipos: TipoDano[]
  errorCatalogos: string | null
}

export default function FiltrosModeracion({ idBase, filtros, onCambiar, colonias, tipos, errorCatalogos }: Props) {
  return (
    <fieldset className="filtros-moderacion">
      <legend>Filtrar</legend>
      <Campo
        id={`${idBase}-colonia`}
        etiqueta="Colonia"
        tipo="select"
        textoOpcionVacia="Todas las colonias"
        valor={filtros.colonia_id}
        onCambio={(valor) => onCambiar({ ...filtros, colonia_id: valor })}
        opciones={colonias.map((c) => ({ valor: String(c.id), etiqueta: c.nombre }))}
      />
      <Campo
        id={`${idBase}-tipo`}
        etiqueta="Tipo de daño"
        tipo="select"
        textoOpcionVacia="Todos los tipos"
        valor={filtros.tipo_dano_codigo}
        onCambio={(valor) => onCambiar({ ...filtros, tipo_dano_codigo: valor })}
        opciones={tipos.map((t) => ({ valor: t.codigo, etiqueta: t.nombre }))}
      />
      {errorCatalogos && <p className="campo-ayuda">No se pudieron cargar las opciones de los filtros: {errorCatalogos}</p>}
    </fieldset>
  )
}
