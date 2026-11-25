"""Regenera docs/arquitectura.png y db/er.png a partir de docs/arquitectura.mmd y db/er.mmd.

Uso (desde la raíz del repositorio):
    python docs/herramientas/generar_diagramas.py

Requisitos: Python 3 (solo biblioteca estándar), Microsoft Edge o Google Chrome instalado e internet
(Mermaid 11.4.1 se descarga desde jsDelivr al renderizar). No agrega dependencias al proyecto.
Variable opcional NAVEGADOR: ruta al ejecutable de Edge/Chrome si no está en la ubicación usual.

Cómo funciona: crea un HTML temporal (fuera del repositorio) que renderiza el .mmd con Mermaid, mide el
diagrama con un primer paso (--dump-dom) y toma la captura con una ventana del tamaño exacto (segundo paso),
para que no se recorte. Fondo blanco, escala x2 para que el texto se lea bien.
"""

import html
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

MERMAID_URL = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"
RAIZ = Path(__file__).resolve().parents[2]
DIAGRAMAS = [
    (RAIZ / "docs" / "arquitectura.mmd", RAIZ / "docs" / "arquitectura.png"),
    (RAIZ / "db" / "er.mmd", RAIZ / "db" / "er.png"),
]
CANDIDATOS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]

PLANTILLA = """<!doctype html>
<html><head><meta charset="utf-8"><style>
html,body{{margin:0;background:#fff;font-family:"Segoe UI",Arial,sans-serif}}
#marco{{display:inline-block;padding:24px;background:#fff}}
</style></head><body>
<div id="marco"><pre class="mermaid" id="d">{fuente}</pre></div>
<script src="{url}"></script>
<script>
mermaid.initialize({{startOnLoad:false,securityLevel:"loose",theme:"default",
  flowchart:{{htmlLabels:true,useMaxWidth:false,nodeSpacing:40,rankSpacing:55,padding:12}},
  er:{{useMaxWidth:false}},fontFamily:'"Segoe UI",Arial,sans-serif',fontSize:15}});
mermaid.run({{querySelector:"#d"}}).then(function(){{
  var r=document.getElementById("marco").getBoundingClientRect();
  document.body.setAttribute("data-medida",JSON.stringify({{w:Math.ceil(r.width),h:Math.ceil(r.height)}}));
}}).catch(function(e){{document.body.setAttribute("data-error",String(e));}});
</script></body></html>
"""


def buscar_navegador() -> str:
    candidatos = [os.environ.get("NAVEGADOR", "")] + CANDIDATOS
    for ruta in candidatos:
        if ruta and Path(ruta).exists():
            return ruta
    sys.exit("No se encontró Edge/Chrome. Define la variable NAVEGADOR con la ruta del ejecutable.")


def ejecutar(navegador: str, *args: str, perfil: Path) -> subprocess.CompletedProcess:
    cmd = [navegador, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
           f"--user-data-dir={perfil}", *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


def generar(navegador: str, mmd: Path, png: Path, tmp: Path) -> None:
    pagina = tmp / (mmd.stem + ".html")
    pagina.write_text(PLANTILLA.format(fuente=html.escape(mmd.read_text(encoding="utf-8")), url=MERMAID_URL),
                      encoding="utf-8")
    uri = pagina.as_uri()
    perfil = tmp / "perfil"
    paso1 = ejecutar(navegador, "--virtual-time-budget=15000", "--dump-dom", uri, perfil=perfil)
    err = re.search(r'data-error="([^"]*)"', paso1.stdout)
    medida = re.search(r"data-medida='([^']*)'", paso1.stdout) or re.search(r'data-medida="([^"]*)"', paso1.stdout)
    if err or not medida:
        sys.exit(f"Mermaid no pudo renderizar {mmd.name}: {err.group(1) if err else 'sin medida'}")
    m = json.loads(html.unescape(medida.group(1)))
    ancho, alto = m["w"] + 8, m["h"] + 8
    png.parent.mkdir(parents=True, exist_ok=True)
    ejecutar(navegador, "--force-device-scale-factor=2", f"--window-size={ancho},{alto}",
             "--virtual-time-budget=15000", f"--screenshot={png}", uri, perfil=perfil)
    if not png.exists():
        sys.exit(f"No se generó {png}")
    print(f"{png.relative_to(RAIZ)}: {ancho * 2}x{alto * 2} px, {png.stat().st_size // 1024} KB")


def main() -> None:
    navegador = buscar_navegador()
    with tempfile.TemporaryDirectory(prefix="liebre_diagramas_") as t:
        for mmd, png in DIAGRAMAS:
            generar(navegador, mmd, png, Path(t))


if __name__ == "__main__":
    main()
