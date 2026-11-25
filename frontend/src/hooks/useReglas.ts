import { useEffect, useState } from 'react'
import { REGLAS_RESPALDO, reglasCompartidas } from '../api/reglas.ts'
import type { Reglas } from '../api/tipos.ts'

// Devuelve las reglas del servidor, o las de respaldo mientras llegan (o si la petición falla)
export function useReglas(): Reglas {
  const [reglas, setReglas] = useState<Reglas>(REGLAS_RESPALDO)

  useEffect(() => {
    let vigente = true
    reglasCompartidas()
      .then((r) => {
        if (vigente) setReglas({ ...REGLAS_RESPALDO, ...r })
      })
      .catch(() => {
        // Se queda con los valores de respaldo
      })
    return () => {
      vigente = false
    }
  }, [])

  return reglas
}
