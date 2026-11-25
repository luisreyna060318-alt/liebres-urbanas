"""Genera docs/REPORTE.pdf a partir de docs/reporte/REPORTE.md y docs/AUTOEVALUACION.md.

Cómo regenerar (Windows, Git Bash o PowerShell):

1. Crear un entorno virtual TEMPORAL fuera del repositorio e instalar solo el paquete `markdown`
   (no es dependencia del proyecto; no se agrega a ningún requirements):

       python -m venv %TEMP%\\venv-reporte
       %TEMP%\\venv-reporte\\Scripts\\python.exe -m pip install markdown

2. Correr este script con ese Python, desde cualquier carpeta:

       %TEMP%\\venv-reporte\\Scripts\\python.exe docs/reporte/generar_pdf.py

El script arma un HTML con estilos sencillos en una carpeta temporal, lo imprime a PDF con Microsoft Edge sin interfaz
(--headless --print-to-pdf --no-pdf-header-footer) y al final dice cuántas páginas salieron.
La autoevaluación no se copia dentro de REPORTE.md: se inserta aquí, en el lugar del comentario `INCLUIR`, para que solo
exista una versión (docs/AUTOEVALUACION.md).

Opciones:
    --edge RUTA     ruta de msedge.exe (por omisión, la instalación normal de Windows)
    --html RUTA     además guarda el HTML generado en esa ruta (útil para revisar en el navegador)
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent  # docs/reporte
DOCS = AQUI.parent  # docs
FUENTE = AQUI / "REPORTE.md"
AUTOEVALUACION = DOCS / "AUTOEVALUACION.md"
SALIDA = DOCS / "REPORTE.pdf"
ESTILOS = AQUI / "estilos.css"
EDGE_POR_OMISION = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

# Marcadores que el equipo debe completar: se resaltan en el PDF para que no se pierdan
MARCADORES = re.compile(
    r"\[(?:PENDIENTE|BORRADOR PARA REVISIÓN|CONDICIONADO|NÚMERO DE CONTROL|Lo llena|Lo escribe)[^\]]*\]"
)


def cargar_markdown():
    try:
        import markdown  # noqa: PLC0415 (se importa aquí para dar un mensaje claro si falta)
    except ImportError:
        sys.exit("Falta el paquete 'markdown'. Instálalo en un entorno virtual temporal (ver la cabecera de este script).")
    return markdown


def armar_markdown() -> str:
    """Une el reporte con la autoevaluación (sección 9) en el lugar del comentario INCLUIR."""
    texto = FUENTE.read_text(encoding="utf-8")
    auto = AUTOEVALUACION.read_text(encoding="utf-8")
    # El título del archivo suelto se vuelve la sección 9 del reporte
    auto = re.sub(r"^## ", "### ", auto, flags=re.M)  # sus subtítulos quedan dentro de la sección 9
    auto = re.sub(r"^# .*$", "## 9. Autoevaluación con la rúbrica", auto, count=1, flags=re.M)
    marca = "<!-- INCLUIR: ../AUTOEVALUACION.md -->"
    if marca not in texto:
        sys.exit(f"No encontré el comentario {marca!r} en {FUENTE.name}")
    return texto.replace(marca, '<div class="autoevaluacion" markdown="1">\n\n' + auto + "\n\n</div>")


def a_html(md_texto: str) -> str:
    markdown = cargar_markdown()
    cuerpo = markdown.markdown(md_texto, extensions=["tables", "fenced_code", "md_in_html", "sane_lists"])

    # Las imágenes usan rutas relativas a docs/reporte/; el HTML vive en una carpeta temporal, así que se vuelven absolutas
    def absoluta(m: re.Match) -> str:
        ruta = (AQUI / m.group(2)).resolve()
        if not ruta.exists():
            sys.exit(f"No existe la figura {ruta}")
        return f'{m.group(1)}"{ruta.as_uri()}"'

    cuerpo = re.sub(r'(<img[^>]*\ssrc=)"(?!https?:|file:)([^"]+)"', absoluta, cuerpo)
    # Resaltar marcadores pendientes (fuera de los bloques de código no aparecen, así que basta con el texto)
    cuerpo = MARCADORES.sub(lambda m: f'<mark class="pendiente">{m.group(0)}</mark>', cuerpo)
    # Las URL sueltas de la portada y las referencias se vuelven enlaces
    # (se saltan las que ya son atributo o texto de un enlace)
    cuerpo = re.sub(r'(?<!["=])(https?://[^\s<)"]+[^\s<).,"])(?![^<]*</a>)', r'<a href="\1">\1</a>', cuerpo)

    estilos = ESTILOS.read_text(encoding="utf-8")
    return (
        '<!doctype html>\n<html lang="es-MX">\n<head>\n<meta charset="utf-8">\n'
        "<title>Liebre Urbana — Reporte técnico</title>\n"
        f"<style>\n{estilos}\n</style>\n</head>\n<body>\n{cuerpo}\n</body>\n</html>\n"
    )


def imprimir_pdf(html: Path, pdf: Path, edge: Path) -> None:
    if not edge.exists():
        sys.exit(f"No encontré Microsoft Edge en {edge}. Usa --edge para indicar otra ruta.")
    # Perfil aparte en la carpeta temporal del sistema: no toca el Edge que la persona tenga abierto ni sus datos.
    # Con un perfil recién creado, Edge a veces termina sin escribir el PDF; por eso se reintenta.
    perfil = Path(tempfile.gettempdir()) / "liebre-reporte-edge"
    for _ in range(3):
        orden = [
            str(edge),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--disable-extensions",
            f"--user-data-dir={perfil}",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf}",
            html.as_uri(),
        ]
        subprocess.run(orden, check=True, capture_output=True, timeout=120)
        # En Windows msedge.exe puede regresar antes de que el proceso de impresión termine: se espera al archivo
        for _ in range(60):
            if pdf.exists() and pdf.stat().st_size > 0:
                time.sleep(1)  # que termine de escribirse
                return
            time.sleep(1)
    sys.exit("Edge no generó el PDF después de 3 intentos.")


def contar_paginas(pdf: Path) -> int:
    datos = pdf.read_bytes()
    return len(re.findall(rb"/Type\s*/Page(?!s)", datos))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--edge", type=Path, default=EDGE_POR_OMISION)
    parser.add_argument("--html", type=Path, help="guardar también el HTML generado")
    args = parser.parse_args()

    html_texto = a_html(armar_markdown())
    with tempfile.TemporaryDirectory(prefix="reporte-") as carpeta:
        html = Path(carpeta) / "REPORTE.html"
        html.write_text(html_texto, encoding="utf-8")
        if args.html:
            shutil.copyfile(html, args.html)
        destino = Path(carpeta) / "REPORTE.pdf"
        imprimir_pdf(html, destino, args.edge)
        shutil.copyfile(destino, SALIDA)

    print(f"PDF generado: {SALIDA} ({contar_paginas(SALIDA)} páginas)")


if __name__ == "__main__":
    main()
