// Al cerrar un formulario sin enviarlo, el botón que lo abrió vuelve a aparecer: se le devuelve el foco, para que quien usa
// teclado no pierda su lugar. Se espera al siguiente cuadro para que React ya haya vuelto a pintar el botón.
export function devolverFoco(idElemento: string): void {
  requestAnimationFrame(() => document.getElementById(idElemento)?.focus())
}
