import { useEffect, useRef } from 'react'

// Un formulario que reemplaza al botón que lo abrió hace que el botón desaparezca y el foco del teclado se pierda
// (WCAG 2.4.3, orden del foco). Este hook pasa el foco al primer campo del formulario cuando aparece:
//   const formulario = useFocoAlMontar<HTMLFormElement>()   ...   <form ref={formulario}>
export function useFocoAlMontar<T extends HTMLElement>() {
  const contenedor = useRef<T>(null)
  useEffect(() => {
    contenedor.current?.querySelector<HTMLElement>('input, select, textarea')?.focus()
  }, [])
  return contenedor
}
