"""Genera docs/REPORTE.docx a partir de docs/reporte/REPORTE.md (y docs/AUTOEVALUACION.md).

Solo usa la biblioteca estándar de Python. Toma de docs/reporte/plantilla/ los estilos, la numeración,
el pie con el número de página, el tema y los logos, y escribe un word/document.xml nuevo.

Uso (desde la raíz del repositorio):
    python docs/reporte/generar_docx.py
    powershell -ExecutionPolicy Bypass -File docs/reporte/convertir_pdf.ps1

Convenciones del Markdown que entiende (además de párrafos, **negrita**, *cursiva*, `código` y [enlaces](url)):
    <!-- portada ... -->            bloque con los datos de la portada (clave: valor por línea)
    <!-- solo-md --> ... <!-- /solo-md -->   texto que solo se ve en GitHub y no va al docx
    <!-- tabla: anchos=1700,2100 tam=18 -->  anchos de columna (twips) y tamaño de letra (medios puntos) de la tabla siguiente
    <!-- salto -->                  salto de página
    <!-- INCLUIR: ruta | 9. -->     inserta otro Markdown; el prefijo se antepone a su título "# "
    ```lenguaje | Leyenda           bloque de código con su línea de leyenda en cursiva
    ![texto](ruta "ancho=15")       figura centrada (ancho en cm)
    Párrafos que empiezan con "Tabla N." o "Figura N."  se convierten en pie de tabla o de figura
    [PENDIENTE: ...]                se resalta en amarillo para que no pase desapercibido
"""

from __future__ import annotations

import datetime
import pathlib
import re
import struct
import sys
import zipfile
from xml.sax.saxutils import escape

RAIZ = pathlib.Path(__file__).resolve().parents[2]
DIR_REPORTE = RAIZ / "docs" / "reporte"
PLANTILLA = DIR_REPORTE / "plantilla"
FUENTE = DIR_REPORTE / "REPORTE.md"
SALIDA = RAIZ / "docs" / "REPORTE.docx"

ANCHO_TEXTO = 12240 - 2 * 1701  # twips útiles entre márgenes (8838)
EMU_POR_CM = 360000
GRIS_PIE = "57606A"
COLOR_CODIGO = "24292E"

NS = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"'
)
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


# ---------------------------------------------------------------- utilidades

def t(texto: str) -> str:
    return f'<w:t xml:space="preserve">{escape(texto)}</w:t>'


def tam_png(ruta: pathlib.Path) -> tuple[int, int]:
    with open(ruta, "rb") as f:
        cabecera = f.read(24)
    if cabecera[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"Solo se admiten PNG: {ruta}")
    return struct.unpack(">II", cabecera[16:24])


class Documento:
    def __init__(self) -> None:
        self.cuerpo: list[str] = []
        self.rels: list[tuple[str, str, str, bool]] = []  # (id, tipo, destino, externo)
        self.medios: dict[str, pathlib.Path] = {}  # nombre en word/media -> archivo
        self.id_dibujo = 0
        self.n_rel = 100

    # relaciones
    def rel(self, tipo: str, destino: str, externo: bool = False) -> str:
        for rid, tp, dst, ext in self.rels:
            if tp == tipo and dst == destino:
                return rid
        self.n_rel += 1
        rid = f"rId{self.n_rel}"
        self.rels.append((rid, tipo, destino, externo))
        return rid

    def imagen(self, ruta: pathlib.Path) -> str:
        nombre = ruta.name
        if nombre in self.medios and self.medios[nombre] != ruta:
            nombre = f"{ruta.parent.name}-{nombre}"
        self.medios[nombre] = ruta
        return self.rel(f"{REL}/image", f"media/{nombre}")

    def dibujo(self, ruta: pathlib.Path, ancho_emu: int) -> str:
        w, h = tam_png(ruta)
        alto_emu = round(ancho_emu * h / w)
        rid = self.imagen(ruta)
        self.id_dibujo += 1
        n = self.id_dibujo
        return (
            '<w:r><w:rPr><w:noProof/></w:rPr><w:drawing>'
            f'<wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{ancho_emu}" cy="{alto_emu}"/>'
            f'<wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="{n}" name="Imagen {n}"/>'
            '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="{escape(ruta.name)}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{ancho_emu}" cy="{alto_emu}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
            '</a:graphicData></a:graphic></wp:inline></w:drawing></w:r>'
        )

    # texto con formato en línea
    def runs(self, texto: str, tam: int | None = None, base: str = "", color: str | None = None,
             tam_codigo: int | None = None) -> str:
        """Convierte el Markdown en línea a runs. `base` son propiedades extra (p. ej. <w:i/>)."""
        salida = []
        for i, trozo in enumerate(re.split(r"(\[PENDIENTE[^\]]*\])", texto)):
            if not trozo:
                continue
            resalte = i % 2 == 1
            salida.append(self._inline(trozo, tam, base, color, tam_codigo, resalte, b=False, it=False))
        return "".join(salida)

    def _rpr(self, tam, base, color, b, it, resalte, codigo=False, enlace=False, tam_codigo=None):
        p = []
        if enlace:
            p.append('<w:rStyle w:val="Hipervnculo"/>')
        if codigo:
            p.append('<w:rFonts w:ascii="Consolas" w:eastAsia="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/>')
        if b:
            p.append("<w:b/>")
        if it or "<w:i/>" in base:
            p.append("<w:i/>")
        if codigo:
            p.append(f'<w:color w:val="{COLOR_CODIGO}"/>')
        elif color and not enlace:
            p.append(f'<w:color w:val="{color}"/>')
        tam_final = (tam_codigo or ((tam or 24) - 3)) if codigo else tam
        if tam_final:
            p.append(f'<w:sz w:val="{tam_final}"/>')
        if resalte:
            p.append('<w:highlight w:val="yellow"/>')
        return f"<w:rPr>{''.join(p)}</w:rPr>" if p else ""

    PATRON = re.compile(
        r"(?P<code>`[^`]+`)|(?P<bold>\*\*.+?\*\*)|(?P<link>\[[^\]]+\]\([^)\s]+\))|(?P<auto><https?://[^>]+>)"
        r"|(?P<ital>(?<![\w*])\*[^*\s][^*]*?\*(?![\w*]))"
    )

    def _inline(self, texto, tam, base, color, tam_codigo, resalte, b, it, enlace_rid=None) -> str:
        out = []
        pos = 0
        for m in self.PATRON.finditer(texto):
            if m.start() > pos:
                out.append(self._run(texto[pos:m.start()], tam, base, color, b, it, resalte, enlace_rid))
            g = m.group()
            if m.group("code"):
                rpr = self._rpr(tam, base, color, b, it, resalte, codigo=True, enlace=bool(enlace_rid),
                                tam_codigo=tam_codigo)
                out.append(f"<w:r>{rpr}{t(g[1:-1])}</w:r>")
            elif m.group("bold"):
                out.append(self._inline(g[2:-2], tam, base, color, tam_codigo, resalte, True, it, enlace_rid))
            elif m.group("ital"):
                out.append(self._inline(g[1:-1], tam, base, color, tam_codigo, resalte, b, True, enlace_rid))
            elif m.group("link"):
                mm = re.match(r"\[([^\]]+)\]\(([^)\s]+)\)", g)
                rid = self.rel(f"{REL}/hyperlink", mm.group(2), externo=True)
                interior = self._inline(mm.group(1), tam, base, color, tam_codigo, resalte, b, it, rid)
                out.append(f'<w:hyperlink r:id="{rid}" w:history="1">{interior}</w:hyperlink>')
            elif m.group("auto"):
                url = g[1:-1]
                rid = self.rel(f"{REL}/hyperlink", url, externo=True)
                interior = self._run(url, tam, base, color, b, it, resalte, rid)
                out.append(f'<w:hyperlink r:id="{rid}" w:history="1">{interior}</w:hyperlink>')
            pos = m.end()
        if pos < len(texto):
            out.append(self._run(texto[pos:], tam, base, color, b, it, resalte, enlace_rid))
        return "".join(out)

    def _run(self, texto, tam, base, color, b, it, resalte, enlace_rid=None) -> str:
        texto = texto.replace("\\*", "*").replace("\\|", "|")
        rpr = self._rpr(tam, base, color, b, it, resalte, enlace=bool(enlace_rid))
        return f"<w:r>{rpr}{t(texto)}</w:r>"

    # bloques
    def parrafo(self, ppr: str, contenido: str) -> None:
        self.cuerpo.append(f"<w:p><w:pPr>{ppr}</w:pPr>{contenido}</w:p>")


PPR_CUERPO = '<w:spacing w:line="360" w:lineRule="auto"/><w:jc w:val="both"/>'
PPR_LISTA = '<w:pStyle w:val="Listaconvietas"/><w:spacing w:line="360" w:lineRule="auto"/><w:jc w:val="both"/>'
PPR_REFERENCIA = '<w:spacing w:line="360" w:lineRule="auto"/><w:ind w:left="709" w:hanging="709"/>'
PPR_PIE = '<w:spacing w:before="40" w:after="240"/><w:jc w:val="center"/>'
PPR_FIGURA = '<w:keepNext/><w:spacing w:before="120"/><w:jc w:val="center"/>'
PPR_LEYENDA_CODIGO = '<w:keepNext/><w:spacing w:before="120" w:after="60"/>'
MAR_CELDA = ('<w:tcMar><w:top w:w="40" w:type="dxa"/><w:left w:w="80" w:type="dxa"/>'
             '<w:bottom w:w="40" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tcMar>')


# ---------------------------------------------------------------- portada

def portada(doc: Documento, datos: dict[str, list[str]]) -> None:
    def linea(texto, despues, tam=None, b=False, jc="center"):
        rpr = ""
        if b or tam:
            rpr = "<w:rPr>" + ("<w:b/>" if b else "") + (f'<w:sz w:val="{tam}"/>' if tam else "") + "</w:rPr>"
        doc.parrafo(f'<w:spacing w:after="{despues}" w:line="288" w:lineRule="auto"/><w:jc w:val="{jc}"/>',
                    f"<w:r>{rpr}{t(texto)}</w:r>")

    logos = PLANTILLA / "word" / "media" / "logos.png"
    doc.parrafo('<w:spacing w:after="400"/><w:jc w:val="center"/>', doc.dibujo(logos, 5580000))
    linea("TECNOLÓGICO NACIONAL DE MÉXICO CAMPUS CIUDAD JUÁREZ", 200, 28)
    linea("INSTITUTO TECNOLÓGICO DE CIUDAD JUÁREZ", 520, 28)
    linea("Programación Web (AEB-1055)", 200)
    linea("Proyecto Final Integrador", 360)
    linea(datos["titulo"][0], 440, b=True)
    integrantes = datos["integrante"]
    for i, fila in enumerate(integrantes):
        nombre, rol = [x.strip() for x in fila.split("|", 1)]
        linea(nombre, 40)
        linea(rol, 280 if i == len(integrantes) - 1 else 200, 20)
    linea("Ingeniería en Sistemas Computacionales", 200)
    linea("Contreras Masse Roberto", 280)
    enlaces = datos["enlace"]
    for i, fila in enumerate(enlaces):
        etiqueta, url = [x.strip() for x in fila.split("|", 1)]
        despues = 320 if i == len(enlaces) - 1 else 40
        doc.parrafo(f'<w:spacing w:after="{despues}" w:line="288" w:lineRule="auto"/><w:jc w:val="center"/>',
                    f'<w:r><w:rPr><w:b/><w:sz w:val="20"/></w:rPr>{t(etiqueta + ":")}</w:r>'
                    f'<w:r><w:rPr><w:sz w:val="20"/></w:rPr>{t(" " + url)}</w:r>')
    doc.parrafo('<w:spacing w:line="288" w:lineRule="auto"/><w:jc w:val="right"/>',
                f"<w:r>{t(datos['fecha'][0])}</w:r>")
    # fin de la sección de portada (sin pie ni número de página)
    doc.cuerpo.append(
        '<w:p><w:pPr><w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1417" w:right="1701" w:bottom="1417" w:left="1701" w:header="709" w:footer="709" w:gutter="0"/>'
        '<w:cols w:space="720"/><w:docGrid w:linePitch="360"/></w:sectPr></w:pPr></w:p>'
    )


# ---------------------------------------------------------------- tablas, código y figuras

def celdas(fila: str) -> list[str]:
    fila = fila.strip()
    if fila.startswith("|"):
        fila = fila[1:]
    if fila.endswith("|"):
        fila = fila[:-1]
    partes = re.split(r"(?<!\\)\|", fila)
    return [p.strip() for p in partes]


def tabla(doc: Documento, filas: list[list[str]], anchos: list[int] | None, tam: int) -> None:
    n = len(filas[0])
    if not anchos or len(anchos) != n:
        largos = [max(len(f[i]) if i < len(f) else 0 for f in filas) + 6 for i in range(n)]
        total = sum(largos)
        anchos = [int(ANCHO_TEXTO * x / total) for x in largos]
    # Las tablas cortas no se parten; las largas pueden partirse (el encabezado se repite), pero nunca dejan
    # sola la primera fila de datos ni separan las dos últimas del pie de tabla.
    juntar_todo = len(filas) <= 6
    xml = [
        '<w:tbl><w:tblPr><w:tblStyle w:val="Tablaconcuadrcula"/><w:tblW w:w="0" w:type="auto"/>'
        '<w:jc w:val="center"/><w:tblLayout w:type="fixed"/>'
        '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>'
        "</w:tblPr><w:tblGrid>" + "".join(f'<w:gridCol w:w="{a}"/>' for a in anchos) + "</w:tblGrid>"
    ]
    for k, fila in enumerate(filas):
        encabezado = k == 0
        inicio = k <= 1
        ultima = k >= len(filas) - 2
        trpr = "<w:cantSplit/>" + ("<w:tblHeader/>" if encabezado else "") + '<w:jc w:val="center"/>'
        xml.append(f"<w:tr><w:trPr>{trpr}</w:trPr>")
        for i in range(n):
            texto = fila[i] if i < len(fila) else ""
            mantener = "<w:keepNext/>" if (juntar_todo or inicio or ultima) else ""
            contenido = doc.runs(f"**{texto}**" if encabezado and texto else texto, tam=tam,
                                 tam_codigo=tam - 2)
            xml.append(f'<w:tc><w:tcPr><w:tcW w:w="{anchos[i]}" w:type="dxa"/>{MAR_CELDA}</w:tcPr>'
                       f"<w:p><w:pPr>{mantener}</w:pPr>{contenido}</w:p></w:tc>")
        xml.append("</w:tr>")
    xml.append("</w:tbl>")
    doc.cuerpo.append("".join(xml))


def codigo(doc: Documento, leyenda: str, lineas: list[str]) -> None:
    if leyenda:
        doc.parrafo(PPR_LEYENDA_CODIGO, doc.runs(leyenda, tam=20, base="<w:i/>", tam_codigo=18))
    rpr = (f'<w:rPr><w:rFonts w:ascii="Consolas" w:eastAsia="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/>'
           f'<w:color w:val="{COLOR_CODIGO}"/><w:sz w:val="18"/></w:rPr>')
    parrafos = "".join(
        f'<w:p><w:pPr><w:keepNext/></w:pPr><w:r>{rpr}{t(linea)}</w:r></w:p>' if i < len(lineas) - 1
        else f'<w:p><w:r>{rpr}{t(linea)}</w:r></w:p>'
        for i, linea in enumerate(lineas)
    )
    borde = '<w:{0} w:val="single" w:sz="4" w:space="0" w:color="D0D7DE"/>'
    doc.cuerpo.append(
        '<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:jc w:val="center"/><w:tblBorders>'
        + "".join(borde.format(x) for x in ("top", "left", "bottom", "right"))
        + '</w:tblBorders><w:tblLayout w:type="fixed"/>'
        '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>'
        f'</w:tblPr><w:tblGrid><w:gridCol w:w="{ANCHO_TEXTO}"/></w:tblGrid>'
        '<w:tr><w:trPr><w:cantSplit/><w:jc w:val="center"/></w:trPr>'
        f'<w:tc><w:tcPr><w:tcW w:w="{ANCHO_TEXTO}" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="F6F8FA"/>'
        '<w:tcMar><w:top w:w="100" w:type="dxa"/><w:left w:w="140" w:type="dxa"/><w:bottom w:w="100" w:type="dxa"/>'
        f'<w:right w:w="140" w:type="dxa"/></w:tcMar></w:tcPr>{parrafos}</w:tc></w:tr></w:tbl>'
    )
    doc.parrafo('<w:spacing w:after="80"/>', "")


# ---------------------------------------------------------------- lector del Markdown

def convertir(doc: Documento, ruta: pathlib.Path, desplazamiento: int, prefijo: str = "") -> None:
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    i = 0
    opciones_tabla: dict[str, str] = {}
    en_referencias = False

    def siguiente_es_bloque(linea: str) -> bool:
        s = linea.strip()
        return (not s or s.startswith(("#", "|", "- ", "```", "<!--", "![")))

    while i < len(lineas):
        linea = lineas[i]
        s = linea.strip()

        if not s:
            i += 1
            continue

        # comentarios y directivas
        if s.startswith("<!--"):
            bloque = [s]
            while "-->" not in bloque[-1]:
                i += 1
                bloque.append(lineas[i].strip())
            i += 1
            texto = "\n".join(bloque)[4:].rsplit("-->", 1)[0].strip()
            if texto == "solo-md":
                while lineas[i].strip() != "<!-- /solo-md -->":
                    i += 1
                i += 1
            elif texto.startswith("portada"):
                datos: dict[str, list[str]] = {}
                for fila in texto.splitlines()[1:]:
                    if ":" in fila:
                        clave, valor = fila.split(":", 1)
                        datos.setdefault(clave.strip(), []).append(valor.strip())
                portada(doc, datos)
            elif texto.startswith("tabla:"):
                opciones_tabla = dict(re.findall(r"(\w+)=(\S+)", texto))
            elif texto == "salto":
                doc.cuerpo.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
            elif texto.startswith("INCLUIR:"):
                partes = [x.strip() for x in texto[len("INCLUIR:"):].split("|")]
                otro = (ruta.parent / partes[0]).resolve()
                convertir(doc, otro, 0, partes[1] + " " if len(partes) > 1 else "")
            continue

        # títulos
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            nivel = len(m.group(1)) - desplazamiento
            texto = m.group(2)
            if nivel == 1 and prefijo:
                texto = prefijo + texto
            estilo = "Ttulo1" if nivel <= 1 else "Ttulo2"
            en_referencias = nivel <= 1 and "Referencias" in texto
            doc.parrafo(f'<w:pStyle w:val="{estilo}"/>', f"<w:r>{t(texto)}</w:r>")
            i += 1
            continue

        # tablas
        if s.startswith("|"):
            filas = []
            while i < len(lineas) and lineas[i].strip().startswith("|"):
                fila = celdas(lineas[i])
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in fila):
                    filas.append(fila)
                i += 1
            anchos = [int(x) for x in opciones_tabla["anchos"].split(",")] if "anchos" in opciones_tabla else None
            tabla(doc, filas, anchos, int(opciones_tabla.get("tam", 20)))
            opciones_tabla = {}
            continue

        # código
        if s.startswith("```"):
            cabecera = s[3:]
            leyenda = cabecera.split("|", 1)[1].strip() if "|" in cabecera else ""
            i += 1
            cuerpo = []
            while not lineas[i].strip().startswith("```"):
                cuerpo.append(lineas[i].rstrip())
                i += 1
            i += 1
            codigo(doc, leyenda, cuerpo)
            continue

        # figuras
        if s.startswith("!["):
            figuras = re.findall(r'!\[[^\]]*\]\(([^)\s]+)(?:\s+"ancho=([\d.]+)")?\)', s)
            contenido = ""
            for destino, ancho in figuras:
                ancho_emu = int(float(ancho) * EMU_POR_CM) if ancho else ANCHO_TEXTO * 635
                contenido += doc.dibujo((ruta.parent / destino).resolve(), ancho_emu)
            doc.parrafo(PPR_FIGURA, contenido)
            i += 1
            continue

        # listas
        if s.startswith("- "):
            while i < len(lineas) and lineas[i].strip().startswith("- "):
                texto = lineas[i].strip()[2:]
                i += 1
                while i < len(lineas) and lineas[i].startswith("  ") and lineas[i].strip() \
                        and not lineas[i].strip().startswith("- "):
                    texto += " " + lineas[i].strip()
                    i += 1
                doc.parrafo(PPR_LISTA, doc.runs(texto))
            continue

        # párrafo normal (o pie de tabla / figura)
        partes = [s.lstrip("> ").strip()]
        i += 1
        while i < len(lineas) and not siguiente_es_bloque(lineas[i]):
            partes.append(lineas[i].strip().lstrip("> ").strip())
            i += 1
        texto = " ".join(partes)
        if re.match(r"^(Tabla|Figura) \d+\.", texto):
            doc.parrafo(PPR_PIE, doc.runs(texto, tam=18, base="<w:i/>", color=GRIS_PIE, tam_codigo=16))
        elif en_referencias:
            doc.parrafo(PPR_REFERENCIA, doc.runs(texto))
        else:
            doc.parrafo(PPR_CUERPO, doc.runs(texto))


# ---------------------------------------------------------------- empaquetado

def empaquetar(doc: Documento) -> None:
    rid_pie = doc.rel(f"{REL}/footer", "footer1.xml")
    cuerpo = "".join(doc.cuerpo)
    documento = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f"<w:document {NS}><w:body>{cuerpo}"
        f'<w:sectPr><w:footerReference w:type="default" r:id="{rid_pie}"/><w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1417" w:right="1701" w:bottom="1417" w:left="1701" w:header="709" w:footer="709" w:gutter="0"/>'
        '<w:cols w:space="720"/><w:docGrid w:linePitch="360"/></w:sectPr></w:body></w:document>'
    )
    fijas = [
        ("rId1", f"{REL}/styles", "styles.xml"),
        ("rId2", f"{REL}/numbering", "numbering.xml"),
        ("rId3", f"{REL}/settings", "settings.xml"),
        ("rId4", f"{REL}/webSettings", "webSettings.xml"),
        ("rId5", f"{REL}/footnotes", "footnotes.xml"),
        ("rId6", f"{REL}/endnotes", "endnotes.xml"),
        ("rId7", f"{REL}/fontTable", "fontTable.xml"),
        ("rId8", f"{REL}/theme", "theme/theme1.xml"),
    ]
    rels = "".join(f'<Relationship Id="{a}" Type="{b}" Target="{c}"/>' for a, b, c in fijas)
    for rid, tipo, destino, externo in doc.rels:
        modo = ' TargetMode="External"' if externo else ""
        rels += f'<Relationship Id="{rid}" Type="{tipo}" Target="{escape(destino, {chr(34): "&quot;"})}"{modo}/>'
    rels_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                f"{rels}</Relationships>")

    tipos = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="png" ContentType="image/png"/>'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="xml" ContentType="application/xml"/>')
    wml = "application/vnd.openxmlformats-officedocument.wordprocessingml."
    for parte, ct in [
        ("/word/document.xml", wml + "document.main+xml"), ("/word/numbering.xml", wml + "numbering+xml"),
        ("/word/styles.xml", wml + "styles+xml"), ("/word/settings.xml", wml + "settings+xml"),
        ("/word/webSettings.xml", wml + "webSettings+xml"), ("/word/footnotes.xml", wml + "footnotes+xml"),
        ("/word/endnotes.xml", wml + "endnotes+xml"), ("/word/footer1.xml", wml + "footer+xml"),
        ("/word/fontTable.xml", wml + "fontTable+xml"),
        ("/word/theme/theme1.xml", "application/vnd.openxmlformats-officedocument.theme+xml"),
        ("/docProps/core.xml", "application/vnd.openxmlformats-package.core-properties+xml"),
        ("/docProps/app.xml", "application/vnd.openxmlformats-officedocument.extended-properties+xml"),
    ]:
        tipos += f'<Override PartName="{parte}" ContentType="{ct}"/>'
    tipos += "</Types>"

    ahora = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            "<dc:creator>Equipo Liebre Urbana</dc:creator><cp:lastModifiedBy>Equipo Liebre Urbana</cp:lastModifiedBy>"
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{ahora}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{ahora}</dcterms:modified>'
            "<dc:language>es-MX</dc:language></cp:coreProperties>")
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
           "<Application>Microsoft Office Word</Application></Properties>")
    paquete_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
                    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
                    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                    "</Relationships>")

    with zipfile.ZipFile(SALIDA, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", tipos)
        z.writestr("_rels/.rels", paquete_rels)
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)
        z.writestr("word/document.xml", documento)
        z.writestr("word/_rels/document.xml.rels", rels_xml)
        for parte in ["styles.xml", "numbering.xml", "settings.xml", "webSettings.xml", "footnotes.xml",
                      "endnotes.xml", "fontTable.xml", "footer1.xml", "theme/theme1.xml"]:
            z.write(PLANTILLA / "word" / parte, f"word/{parte}")
        for nombre, archivo in doc.medios.items():
            z.write(archivo, f"word/media/{nombre}")


def main() -> None:
    doc = Documento()
    convertir(doc, FUENTE, desplazamiento=1)
    empaquetar(doc)
    print(f"Escrito {SALIDA.relative_to(RAIZ)} ({SALIDA.stat().st_size // 1024} KB, "
          f"{len(doc.medios)} imágenes, {sum(1 for r in doc.rels if r[3])} enlaces)")


if __name__ == "__main__":
    sys.exit(main())
