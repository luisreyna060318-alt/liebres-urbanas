# Fuente de las colonias de demostración (RNF-09)

Este documento explica de dónde salen los datos de `colonias_juarez.csv`, cómo se eligieron y qué límites tienen.
El archivo trae **23 asentamientos reales de Ciudad Juárez** (cumple el mínimo de 20 de RNF-09; ver la sección de
limitaciones sobre por qué no son más).

## 1. Fuente oficial

| Dato | Valor |
|---|---|
| Catálogo | Catálogo Nacional de Códigos Postales |
| Institución | Correos de México (Servicio Postal Mexicano) |
| Página oficial de descarga | <https://www.correosdemexico.gob.mx/SSLServicios/ConsultaCP/CodigoPostal_Exportar.aspx> |
| Forma de descarga | Formulario de la página: estado "Chihuahua", formato "TXT" |
| Fecha de descarga | 24 de noviembre de 2026, 23:29 (hora de Ciudad Juárez); 25 de noviembre de 2026, 06:29 UTC según el encabezado HTTP |
| Archivo recibido | `Chihuahua.txt` (el servidor lo entrega con `Content-Disposition: attachment; filename=Chihuahua.txt`) |
| Tamaño | 931 382 bytes (909.6 KiB) |
| SHA-256 | `73e9148d65eb04bf62df9454902d6596f8fb73bc9593936ff5037f546249c75c` |
| Codificación y formato | ISO-8859-1 (latin-1), campos separados por `|`; línea 1 = aviso legal, línea 2 = encabezado |
| Contenido | 10 135 asentamientos del estado de Chihuahua, de los cuales 1 158 son del municipio de Juárez (clave de municipio `037`) |

El archivo original **no se incluye en el repositorio** (ver términos de uso). Quien quiera reproducir el CSV debe
descargarlo de la misma página.

### Términos de uso que declara la fuente

El propio archivo abre con este aviso: "El Catálogo Nacional de Códigos Postales, es elaborado por Correos de México y
se proporciona en forma gratuita para uso particular, no estando permitida su comercialización, total o parcial, ni su
distribución a terceros bajo ningún concepto." La página de descarga repite que se entrega gratis y que no se permite
su comercialización.

Por eso el repositorio solo guarda una **muestra de 23 renglones** (código postal, nombre y tipo del asentamiento)
con fines escolares y no comerciales, y no el catálogo completo. Si el proyecto se usara fuera de la escuela habría
que revisar este punto con Correos de México.

## 2. Cómo se filtró y se eligió la muestra

1. Se leyó el archivo con la codificación latin-1 y se conservaron los registros con `c_estado = 08` (Chihuahua) y
   `c_mnpio = 037` (Juárez): 1 158 asentamientos.
2. Se tomaron como candidatos los de tipo Colonia y Fraccionamiento (más algunos Condominio y Unidad habitacional con
   nombre propio) y se descartaron los nombres repetidos dentro del municipio (por ejemplo, "Altavista" existe como
   colonia y como condominio) y los genéricos con números, "Ampliación", "Cerrada" o "Privada".
3. De esos candidatos (más de 600 nombres) **entraron solo los que se pudieron ubicar con datos de OpenStreetMap** (sección
   3). No se inventó ninguna coordenada: si un asentamiento no apareció como zona en OpenStreetMap, no entró.
4. De cada fila se conserva el código postal y el tipo de asentamiento tal como vienen en la fuente.

La lista final está fija en `NOMBRES_ELEGIDOS` dentro de `preparar_colonias.py`. El script comprueba que cada nombre
exista en el catálogo con ese código postal y que no esté repetido en el municipio.

## 3. Cómo se obtuvieron las coordenadas

Las coordenadas son **centroides aproximados** (un punto representativo de la zona de la colonia, no su centro
geométrico exacto) obtenidos con Nominatim, el buscador de OpenStreetMap:

- Servicio: `https://nominatim.openstreetmap.org/search`, `format=jsonv2`, consulta `q=<colonia>, Ciudad Juárez, Chihuahua`.
- Una petición por segundo como máximo y `User-Agent: LiebreUrbana-proyecto-escolar` (sin correos ni datos personales),
  según la política de uso de Nominatim.
- Se pidieron hasta 5 resultados por consulta (no solo 1), porque Nominatim suele poner primero una calle con el mismo
  nombre. Si la primera consulta no sirve, se prueba con `<tipo> <colonia>, Ciudad Juárez, Chihuahua`.
- Solo se acepta un resultado que sea la **zona residencial o el barrio** de OpenStreetMap (`place=suburb`,
  `neighbourhood` o `quarter`, o `landuse=residential`) y cuyo nombre coincida exactamente con el del catálogo
  (se ignoran acentos, mayúsculas, el prefijo "Colonia"/"Fraccionamiento" y artículos como "de" o "del").
  Se rechazan calles, parques, comercios y nombres parecidos pero distintos (por ejemplo, "Infomavit Solidaridad" para
  "Solidaridad").
- Se valida que el punto caiga en la zona urbana de Juárez: latitud 31.55 a 31.82 y longitud -106.62 a -106.20.
  Los que quedan fuera se descartan.
- Los 23 renglones finales salieron todos como zona de OpenStreetMap y dentro del rango.

Datos de ubicación © colaboradores de OpenStreetMap, disponibles bajo la licencia ODbL 1.0
(<https://www.openstreetmap.org/copyright>). El CSV derivado conserva esa atribución.

Se consultaron más de 600 asentamientos y entraron 23. La mayoría de las colonias del centro, norte y poniente
(por ejemplo Partido Romero, Obrera, Chaveña, Pronaf, Fronteriza, Anapra, Plutarco Elías Calles, Satélite, Fuentes del
Valle) no están mapeadas como zona en OpenStreetMap, o Nominatim solo devolvió calles o parques con ese nombre, así
que **no entraron**.

## 4. Cómo se asignaron los sectores

Los sectores son una agrupación propia de la asociación y **no son oficiales**. Se usan exactamente cinco nombres:
Centro, Norponiente, Nororiente, Surponiente y Suroriente. La regla es geográfica y reproducible
(función `asignar_sector` de `preparar_colonias.py`):

1. **Centro**: el punto está a 2 km o menos de la Catedral / Plaza de Armas (31.7389, -106.4870), distancia
   calculada con la fórmula de haversine.
2. Fuera de ese radio se usan dos cortes:
   - latitud de corte **31.69**: mayor o igual es norte, menor es sur;
   - longitud de corte **-106.43**: menor es poniente, mayor o igual es oriente.

   Resultan Norponiente, Nororiente, Surponiente y Suroriente.

Reparto actual: Centro 3, Norponiente 3, Nororiente 3, Surponiente 6, Suroriente 8.

**Los cortes se fijaron a mano para que cada sector tuviera al menos 3 colonias** con la muestra disponible, que
quedó cargada hacia el sur y el oriente porque ahí es donde OpenStreetMap tiene más zonas mapeadas. Una consecuencia
visible es que "Azteca" (unos 5 km al sur de la Catedral) cae en Norponiente. Si en el futuro se agregan colonias
del norte y poniente, conviene mover los cortes hacia la Catedral (31.7389, -106.4870) para que los nombres de los
sectores coincidan mejor con la geografía.

## 5. Limitaciones

- Coordenadas **aproximadas** (centroide de una zona de OpenStreetMap, redondeado a 5 decimales); sirven para ubicar
  la colonia en un mapa de demostración, no para medir ni para trámites.
- Sectores **no oficiales**, con cortes ajustados a la muestra (ver sección 4).
- La muestra es de 23 asentamientos, no de 30 o más, porque el resto no se pudo ubicar sin inventar datos. Cumple el
  mínimo de 20 de RNF-09, pero el norte y el poniente están poco representados.
- Algunos nombres son poco conocidos (por ejemplo "Pie de Casa (El Granjero)") o genéricos ("Durango", "Del Real"),
  pero existen en el catálogo y son únicos en el municipio.
- El catálogo se actualiza con el tiempo; los códigos postales y nombres son los de la fecha de descarga.

## 6. Cómo reproducir el CSV

```bash
# 1) Bajar Chihuahua.txt de la página oficial (arriba) y guardarlo FUERA del repositorio.
# 2) Sin red (usa el CSV actual como archivo de coordenadas):
python -I db/datos/preparar_colonias.py preparar RUTA/Chihuahua.txt salida.csv --coordenadas db/datos/colonias_juarez.csv
# 3) Con red (paso separado; 1 petición por segundo, tarda unos minutos):
python -I db/datos/preparar_colonias.py geocodificar RUTA/Chihuahua.txt coordenadas.csv
python -I db/datos/preparar_colonias.py preparar RUTA/Chihuahua.txt salida.csv --coordenadas coordenadas.csv
```

## 7. Citas (APA 7)

Correos de México. (s. f.). *Catálogo Nacional de Códigos Postales* [Conjunto de datos, archivo Chihuahua.txt]. Servicio
Postal Mexicano. Recuperado el 24 de noviembre de 2026, de
https://www.correosdemexico.gob.mx/SSLServicios/ConsultaCP/CodigoPostal_Exportar.aspx

Colaboradores de OpenStreetMap. (2026). *OpenStreetMap* [Base de datos geográfica; consultada con Nominatim]. Fundación
OpenStreetMap. Recuperado el 24 de noviembre de 2026, de https://www.openstreetmap.org
