"""Reglas de negocio y valores permitidos, documentados en UN solo lugar (DISENO_TECNICO, sección 4).

El cliente permite ajustar estas cifras si se documentan y se respetan en toda la plataforma: por eso los
servicios, los esquemas, las restricciones de la base y el endpoint GET /api/reglas (que usa el frontend)
leen de aquí en lugar de repetir los números.
"""

# --- Duplicados, vigencia y zona ---
RADIO_DUPLICADO_BACHE_M = 30
RADIO_DUPLICADO_ENCHARCAMIENTO_M = 50
VIGENCIA_ENCHARCAMIENTO_HORAS = 6  # desde la creación o desde la última confirmación "sigue"
DESMENTIDOS_PARA_CERRAR = 3  # personas distintas que dicen "ya no hay agua"
RADIO_ZONA_KM = 1  # "¿Cómo está mi zona?"
MAX_RESULTADOS_ZONA = 50  # tope de reportes que devuelve GET /api/zona (el total real va aparte)

# --- Límites ---
MAX_REPORTES_POR_HORA = 10  # por cuenta; se cuenta en la base de datos
DESCRIPCION_MAX = 500  # caracteres
COMENTARIO_MAX = 500  # comentario público de un cambio de estado
PASSWORD_MIN = 8  # con letras y números
NOMBRE_MIN = 2
NOMBRE_MAX = 80
NOMBRE_COLONIA_MIN = 2  # administración de colonias y sectores (HU-06.1)
NOMBRE_COLONIA_MAX = 120
NOMBRE_SECTOR_MAX = 80
FUENTE_COLONIA_MANUAL = "Alta manual (coordinación)"  # `fuente` de las colonias que crea el coordinador (RNF-09)

# --- Sesión ---
INACTIVIDAD_MIN = 30  # el token dura 30 min; el frontend lo renueva (refresh) mientras hay actividad

# --- Paginación ---
TAM_PAGINA_MIS_REPORTES = 10
TAM_PAGINA_CONSULTA = 20
TAM_PAGINA_CATALOGOS = 10  # catálogos y usuarios
TAM_PAGINA_MODERACION = 10  # bandeja de revisión y seguimiento de reparaciones
TAM_PAGINA_MAX = 100  # máximo general que acepta ?tam=
TAM_PAGINA_MAX_COLONIAS = 500  # las colonias se piden completas para llenar listas desplegables

# --- Tablero de indicadores (HU-07.1) ---
TABLERO_TOP_COLONIAS = 10  # colonias con más baches abiertos
TABLERO_MAS_LONGEVOS = 10  # baches abiertos más antiguos
TABLERO_SEMANAS = 12  # semanas de la gráfica de reportes por semana (empiezan en lunes, hora de Juárez)

# --- Clima y puntos recurrentes ---
UMBRAL_LLUVIA_PCT = 30  # probabilidad máxima en las próximas 12 h para mostrar el aviso
HORAS_PRONOSTICO = 12
CACHE_PRONOSTICO_HORAS = 1
PUNTO_RECURRENTE_DIAS = 3  # P1: días distintos del año...
PUNTO_RECURRENTE_RADIO_M = 50  # ...dentro de este radio

# --- Zona horaria (RN-02): se guarda en UTC y se muestra en la hora de Juárez ---
ZONA_HORARIA = "America/Ciudad_Juarez"

# =====================================================================================================
# Valores permitidos (CONTRATO_API, sección 2). Se guardan sin acentos; la interfaz muestra la etiqueta.
# Las restricciones CHECK de la base de datos se arman con estas mismas tuplas.
# =====================================================================================================
ROLES = ("ciudadano", "moderador", "coordinador")
ROL_INICIAL = "ciudadano"  # toda cuenta nueva nace ciudadana (HU-01.1 CA1)

CATEGORIAS = ("bache", "encharcamiento")
TIPOS_DANO = ("bache", "hundimiento", "grieta", "alcantarilla_sin_tapa")
TAMANOS = ("chico", "mediano", "grande")
PROFUNDIDADES = ("baja", "media", "alta")
CARRILES = ("orilla", "izquierdo", "derecho", "varios")
SEVERIDADES = ("baja", "media", "alta")
NIVELES_AGUA = ("a_un_lado", "cubre_carril", "media_llanta", "intransitable")

ESTADOS_BACHE = ("recibido", "validado", "en_reparacion", "reparado", "rechazado")
ESTADOS_ENCHARCAMIENTO = ("activo", "historico", "rechazado")
ESTADO_INICIAL = {"bache": "recibido", "encharcamiento": "activo"}

TIPOS_CONFIRMACION = ("confirma", "sigue", "ya_no_hay")

# Prefijo del folio por categoría: BCH-2026-000123, ENC-2026-000045 (RN-03)
PREFIJOS_FOLIO = {"bache": "BCH", "encharcamiento": "ENC"}


def valores_sql(valores: tuple[str, ...]) -> str:
    """Convierte ("a", "b") en "('a', 'b')" para usarlo dentro de un CHECK ... IN (...)."""
    return "(" + ", ".join(f"'{v}'" for v in valores) + ")"

# --- Municipio de Juárez (RN-01) ---
# Rectángulo (lat_min, lat_max, lon_min, lon_max) que cubre TODO el municipio de Juárez, Chihuahua.
# Fuente: "boundingbox" del límite administrativo municipal en OpenStreetMap (relación 5605951,
# "Juárez, Chihuahua, México"), consultado en Nominatim el 2026-11-24 (datos © colaboradores de OpenStreetMap, ODbL).
# Es una validación aproximada y que funciona sin internet: el rectángulo también toca un poco de El Paso, Texas,
# y del desierto vecino; por eso la búsqueda de direcciones además se limita a México (countrycodes=mx).
MUNICIPIO_BBOX = (31.1199567, 31.7838974, -106.9516255, -106.1808825)

# --- Ubicación con Nominatim (DISENO_TECNICO, sección 6) ---
GEO_MAX_RESULTADOS = 5  # resultados de una búsqueda de dirección
GEO_BUSQUEDA_MIN = 3  # caracteres mínimos para buscar (no se busca "mientras se escribe")
GEO_BUSQUEDA_MAX = 200
GEO_TIEMPO_ESPERA_S = 5  # si Nominatim no responde en 5 s -> 503
GEO_INTERVALO_MIN_S = 1.0  # política de uso de Nominatim: máximo 1 petición por segundo
GEO_ESPERA_MAX_S = 3  # si la fila de búsquedas tarda más que esto en dar turno -> 503 (no se acumulan hilos)
GEO_CACHE_MIN = 60  # una misma búsqueda se responde de memoria durante 1 hora
