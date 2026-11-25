#!/usr/bin/env python3
"""Prepara db/datos/colonias_juarez.csv a partir del catalogo oficial de Correos de Mexico.

Solo usa la biblioteca estandar. Tiene dos subcomandos:

  preparar      (sin red) Lee el catalogo descargado, filtra Chihuahua / municipio de Juarez,
                toma la lista fija de asentamientos de NOMBRES_ELEGIDOS, les asigna sector con
                una regla geografica y escribe el CSV final.
                  python -I preparar_colonias.py preparar CATALOGO.txt SALIDA.csv
                      [--coordenadas COORDS.csv]

  geocodificar  (USA RED, paso manual y aparte) Consulta Nominatim/OpenStreetMap, 1 peticion
                por segundo, para obtener un centroide aproximado por asentamiento y lo guarda
                en un CSV de coordenadas (nombre,lat,lon). Solo hay que correrlo si no se
                tienen las coordenadas; el CSV ya publicado (colonias_juarez.csv) sirve como
                archivo de coordenadas para volver a ejecutar `preparar` sin red.
                  python -I preparar_colonias.py geocodificar CATALOGO.txt COORDS.csv

El catalogo (Chihuahua.txt, ISO-8859-1, separado por |) NO se incluye en el repositorio;
ver FUENTE.md.
"""
import argparse
import csv
import json
import math
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

CODIFICACION_CATALOGO = "latin-1"  # ISO-8859-1, tal como lo entrega Correos de Mexico
CLAVE_ESTADO = "08"  # Chihuahua
CLAVE_MUNICIPIO = "037"  # Juarez

# Lista fija de asentamientos elegidos: (codigo postal, nombre tal como viene en el catalogo).
NOMBRES_ELEGIDOS = [
    ("32000", "Centro"),
    ("32010", "Cuauhtémoc"),
    ("32160", "Durango"),
    ("32300", "Hidalgo"),
    ("32140", "Postal"),
    ("32280", "Azteca"),
    ("32410", "Puerta del Sol"),
    ("32500", "Tecnológico"),
    ("32618", "Pradera Dorada"),
    ("32680", "Lomas de San José"),
    ("32651", "Lomas del Rey"),
    ("32660", "Del Real"),
    ("32662", "Erendira"),
    ("32663", "Prados de Santa Anita"),
    ("32685", "Ciénega Residencial"),
    ("32685", "Urbiquinta Granada"),
    ("32690", "El Granjero"),
    ("32693", "Pie de Casa (El Granjero)"),
    ("32580", "Salvarcar"),
    ("32696", "Paseos del Alba"),
    ("32594", "Riveras del Bravo"),
    ("32674", "Granjas Polo Gamboa"),
    ("32674", "Granjas Santa Elena"),
]

# --- Sectores (agrupacion de la asociacion, NO oficial) ---------------------------------
SECTORES = ["Centro", "Norponiente", "Nororiente", "Surponiente", "Suroriente"]
# Origen de la regla: Catedral / Plaza de Armas de Ciudad Juarez.
CENTRO_LAT = 31.7389
CENTRO_LON = -106.4870
RADIO_CENTRO_KM = 2.0
# Fuera del radio: norte/sur segun la latitud de corte y poniente/oriente segun la longitud de
# corte. Los cortes son una decision de la asociacion (no oficial): se fijaron a mano para que
# la muestra quede repartida en los cinco sectores (ver FUENTE.md).
LAT_CORTE = 31.69   # lat >= corte: norte; lat < corte: sur
LON_CORTE = -106.43  # lon < corte: poniente; lon >= corte: oriente

# Rango de validez (zona urbana de Juarez).
LAT_MIN, LAT_MAX = 31.55, 31.82
LON_MIN, LON_MAX = -106.62, -106.20

# --- Nominatim (solo subcomando geocodificar) -------------------------------------------
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "LiebreUrbana-proyecto-escolar"
# Nominatim ordena por relevancia y a veces pone primero una calle con el mismo nombre; se piden
# unos pocos resultados y se elige el primero que sea un asentamiento (ver es_asentamiento_osm).
LIMITE_RESULTADOS = 5
PAUSA_SEGUNDOS = 1.1  # politica de uso: maximo 1 peticion por segundo
# Objetos de OSM aceptados como "zona de la colonia": (categoria, tipo).
TIPOS_OSM_ACEPTADOS = (
    ("place", "suburb"),
    ("place", "neighbourhood"),
    ("place", "quarter"),
    ("landuse", "residential"),
)
PREFIJOS_NOMBRE_OSM = ("colonia", "fraccionamiento")
ARTICULOS = ("de", "del", "la", "las", "los", "el")

COLUMNAS_CSV = ["cp", "nombre", "tipo_asentamiento", "sector", "lat", "lon"]


def distancia_km(lat1, lon1, lat2, lon2):
    """Distancia haversine en kilometros."""
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def asignar_sector(lat, lon):
    """Regla reproducible: radio de 2 km desde la Catedral = Centro; fuera, cuadrante por cortes."""
    if distancia_km(lat, lon, CENTRO_LAT, CENTRO_LON) <= RADIO_CENTRO_KM:
        return "Centro"
    norte = lat >= LAT_CORTE
    poniente = lon < LON_CORTE
    if norte:
        return "Norponiente" if poniente else "Nororiente"
    return "Surponiente" if poniente else "Suroriente"


def en_rango(lat, lon):
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX


def leer_asentamientos_juarez(ruta_catalogo):
    """Devuelve {(cp, nombre): tipo} de todos los asentamientos del municipio de Juarez.

    Formato del archivo: linea 1 = aviso legal, linea 2 = encabezado, resto = registros
    separados por |. Campos usados: d_codigo, d_asenta, d_tipo_asenta, c_estado, c_mnpio.
    """
    with open(ruta_catalogo, encoding=CODIFICACION_CATALOGO, newline="") as f:
        lineas = f.read().splitlines()
    encabezado = lineas[1].split("|")
    idx = {n: i for i, n in enumerate(encabezado)}
    res = {}
    for linea in lineas[2:]:
        c = linea.split("|")
        if len(c) < len(encabezado):
            continue
        if c[idx["c_estado"]] != CLAVE_ESTADO or c[idx["c_mnpio"]] != CLAVE_MUNICIPIO:
            continue
        res[(c[idx["d_codigo"]], c[idx["d_asenta"]])] = c[idx["d_tipo_asenta"]]
    return res


def resolver_elegidos(asentamientos):
    """Verifica que cada nombre elegido exista en el catalogo y que no se repita."""
    nombres = [n for _, n in NOMBRES_ELEGIDOS]
    if len(set(nombres)) != len(nombres):
        sys.exit("Error: hay nombres repetidos en NOMBRES_ELEGIDOS")
    por_nombre = {}
    for (cp, nom) in asentamientos:
        por_nombre.setdefault(nom, []).append(cp)
    resultado = []
    for cp, nombre in NOMBRES_ELEGIDOS:
        tipo = asentamientos.get((cp, nombre))
        if tipo is None:
            sys.exit(f"Error: {nombre} ({cp}) no esta en el catalogo de Juarez")
        if len(por_nombre[nombre]) > 1:
            sys.exit(f"Error: el nombre {nombre} esta duplicado en el municipio; elegir otro")
        resultado.append((cp, nombre, tipo))
    return resultado


def cargar_coordenadas(ruta):
    """Lee un CSV con columnas nombre,lat,lon (puede traer mas columnas)."""
    coords = {}
    with open(ruta, encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f):
            coords[fila["nombre"]] = (float(fila["lat"]), float(fila["lon"]))
    return coords


def preparar(args):
    elegidos = resolver_elegidos(leer_asentamientos_juarez(args.catalogo))
    coords = cargar_coordenadas(args.coordenadas) if args.coordenadas else {}
    filas, omitidos = [], []
    for cp, nombre, tipo in elegidos:
        if nombre not in coords:
            omitidos.append((nombre, "sin coordenadas"))
            continue
        lat, lon = coords[nombre]
        if not en_rango(lat, lon):
            omitidos.append((nombre, f"fuera de rango ({lat}, {lon})"))
            continue
        filas.append([cp, nombre, tipo, asignar_sector(lat, lon), f"{lat:.5f}", f"{lon:.5f}"])
    with open(args.salida, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(COLUMNAS_CSV)
        w.writerows(filas)
    print(f"Escritas {len(filas)} filas en {args.salida}")
    for nombre, motivo in omitidos:
        print(f"  omitido: {nombre} ({motivo})", file=sys.stderr)
    return 0 if not omitidos else 1


# ======================================================================================
# PASO DE RED: solo este subcomando hace peticiones a internet (Nominatim/OpenStreetMap).
# Datos de ubicacion (c) colaboradores de OpenStreetMap, licencia ODbL.
# ======================================================================================
def _normalizar(texto):
    """Minusculas y sin acentos, para comparar nombres."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn"
    )


def _clave_nombre(texto):
    """Nombre normalizado, sin prefijos "Colonia"/"Fraccionamiento" ni articulos/preposiciones."""
    palabras = _normalizar(texto).split()
    if palabras and palabras[0] in PREFIJOS_NOMBRE_OSM:
        palabras = palabras[1:]
    return " ".join(p for p in palabras if p not in ARTICULOS)


CLAVES_DIRECCION_OSM = ("suburb", "neighbourhood", "quarter", "city_district")


def clasificar_resultado(resultado, nombre):
    """Dice como un resultado de Nominatim se relaciona con el asentamiento `nombre`.

    - "zona": el resultado ES la zona residencial o barrio de OSM con ese nombre (coincidencia
      exacta de nombre, ignorando prefijos Colonia/Fraccionamiento y articulos).
    - "direccion": el resultado es otro objeto (calle, parque, comercio...) cuya direccion en
      OSM dice que esta dentro de la colonia con ese nombre; el punto cae dentro de ella.
    - None: no sirve (calle homonima en otra parte, parque, comercio, nombre parecido pero distinto).
    """
    clave = _clave_nombre(nombre)
    if (resultado.get("category"), resultado.get("type")) in TIPOS_OSM_ACEPTADOS:
        if _clave_nombre(resultado.get("name") or "") == clave:
            return "zona"
        return None
    direccion = resultado.get("address") or {}
    for k in CLAVES_DIRECCION_OSM:
        if k in direccion and _clave_nombre(direccion[k]) == clave:
            return "direccion"
    return None


def consultar_nominatim(texto):
    """Devuelve la lista de resultados (hasta LIMITE_RESULTADOS) de una busqueda en Nominatim."""
    consulta = urllib.parse.urlencode({"q": texto, "format": "jsonv2", "addressdetails": 1, "limit": LIMITE_RESULTADOS})
    req = urllib.request.Request(f"{NOMINATIM_URL}?{consulta}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        datos = json.load(resp)
    time.sleep(PAUSA_SEGUNDOS)
    return datos


def buscar_asentamiento(nombre, tipo):
    """Prueba `<nombre>, Ciudad Juarez, Chihuahua` y, si no sirve, `<tipo> <nombre>, ...`.

    Devuelve (resultado, metodo) con metodo "zona" o "direccion" (ver clasificar_resultado), o
    (primer resultado, None) si ninguno sirve, o (None, None) si no hubo resultados.
    """
    primero = None
    for texto in (f"{nombre}, Ciudad Juárez, Chihuahua", f"{tipo} {nombre}, Ciudad Juárez, Chihuahua"):
        resultados = consultar_nominatim(texto)
        primero = primero or (resultados[0] if resultados else None)
        for metodo in ("zona", "direccion"):
            for r in resultados:
                if clasificar_resultado(r, nombre) == metodo:
                    return r, metodo
    return primero, None


def geocodificar(args):
    elegidos = resolver_elegidos(leer_asentamientos_juarez(args.catalogo))
    with open(args.salida, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["nombre", "lat", "lon", "metodo", "categoria_osm", "tipo_osm", "nombre_osm", "estado"])
        for _, nombre, tipo in elegidos:
            try:
                r, metodo = buscar_asentamiento(nombre, tipo)
            except Exception as e:  # red caida, limite de uso, etc.
                print(f"  fallo {nombre}: {e}", file=sys.stderr)
                continue
            if r is None:
                print(f"  sin resultado: {nombre}")
                continue
            lat, lon = float(r["lat"]), float(r["lon"])
            if metodo is None:
                estado = "descartado: no es un asentamiento de OSM"
            elif not en_rango(lat, lon):
                estado = "descartado: fuera de rango"
            else:
                estado = "ok"
            print(f"  {estado}: {nombre} -> {lat:.5f}, {lon:.5f} [{metodo}; {r['category']}/{r['type']}]")
            w.writerow([nombre, f"{lat:.5f}", f"{lon:.5f}", metodo or "", r["category"], r["type"],
                        r.get("name", ""), estado])
            f.flush()
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("preparar", help="genera el CSV (sin red)")
    p.add_argument("catalogo", help="ruta de Chihuahua.txt descargado de Correos de Mexico")
    p.add_argument("salida", help="ruta del CSV de salida")
    p.add_argument("--coordenadas", help="CSV con columnas nombre,lat,lon ya obtenidas")
    p.set_defaults(fn=preparar)
    g = sub.add_parser("geocodificar", help="USA RED: consulta Nominatim, 1 peticion por segundo")
    g.add_argument("catalogo", help="ruta de Chihuahua.txt descargado de Correos de Mexico")
    g.add_argument("salida", help="ruta del CSV de coordenadas a escribir")
    g.set_defaults(fn=geocodificar)
    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
