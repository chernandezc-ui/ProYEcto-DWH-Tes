"""
rutas.py
========
Mapeo carpeta de entrada → tabla Bronce destino.
El ETL usa este diccionario para saber a qué tabla va cada archivo.
"""

from pathlib import Path
import json
import re
import unicodedata


# Carpeta raíz donde el usuario deposita los Excel de campo
CARPETA_ENTRADA = Path(__file__).parent.parent / 'data' / 'entrada'

# Carpeta donde se archivan los Excel ya procesados
CARPETA_PROCESADOS = Path(__file__).parent.parent / 'data' / 'procesados'

# Carpeta donde se mueven archivos rechazados por layout o enrutamiento.
CARPETA_RECHAZADOS = Path(__file__).parent.parent / 'data' / 'rechazados'


# Mapeo carpeta → tabla Bronce
# Clave   : nombre exacto de la subcarpeta en data/entrada/
# Valor   : nombre completo de la tabla destino en SQL Server
RUTAS: dict[str, str] = {
    'conteo_fruta':              'Bronce.Conteo_Fruta',
    'peladas':                   'Bronce.Peladas',
    'ciclos_fenologicos':        'Bronce.Ciclos_Fenologicos',
    'evaluacion_pesos':          'Bronce.Evaluacion_Pesos',
    'induccion_floral':          'Bronce.Induccion_Floral',
    'floracion':                 'Bronce.Floracion',
    'evaluacion_vegetativa':     'Bronce.Evaluacion_Vegetativa',
    'tasa_crecimiento_brotes':   'Bronce.Tasa_Crecimiento_Brotes',
    'evaluacion_calidad_poda':   'Bronce.Evaluacion_Calidad_Poda',
    'fisiologia':                'Bronce.Fisiologia',
    'calibres':                  'Bronce.Calibres',
    'tareos':                    'Bronce.Consolidado_Tareos',
    'fiscalizacion':             'Bronce.Fiscalizacion',
    'seguimiento_errores':       'Bronce.Seguimiento_Errores',
    'pintado_flores':            'Bronce.Pintado_Flores',
    'reporte_cosecha':           'Bronce.Reporte_Cosecha',
    'cierre_mapas_cosecha':      'Bronce.Cierre_Mapas_Cosecha',
    'reporte_clima':             'Bronce.Reporte_Clima',
    'data_sap':                  'Bronce.Data_SAP',
    'proyeccion_pesos':          'Bronce.Proyeccion_Pesos',
    'telemetria_clima':          'Bronce.Telemetria_Clima',
    'base_plantas_area':         'Bronce.Base_Plantas_Area',
    'censo_plantas':             'Bronce.Censo_Plantas',
}

ALIAS_CARPETAS: dict[str, str] = {
    'evaluacion_vegetativa_arandano': 'evaluacion_vegetativa',
    'evaluacion_peso':                'evaluacion_pesos',
    'evaluacion_pesos_reporte':       'evaluacion_pesos',
    'fenologia':                      'conteo_fruta',
}

ALIAS_ARCHIVOS: dict[str, str] = {
    'reporte_evaluacion_peso':        'evaluacion_pesos',
    'evaluacion_peso':                'evaluacion_pesos',
    'evaluacion_pesos':               'evaluacion_pesos',
    'evaluacion_vegetativa':          'evaluacion_vegetativa',
    'vegetativa_arandano':            'evaluacion_vegetativa',
    'tasa_crecimiento':               'tasa_crecimiento_brotes',
    'floracion':                      'floracion',
    'fenologia':                      'conteo_fruta',
    'meteorologia':                   'telemetria_clima',
}


def _normalizar_nombre(texto: str) -> str:
    """
    Normaliza texto para comparacion:
    - elimina acentos
    - minusculas
    - separadores/puntuacion -> underscore
    """
    texto = unicodedata.normalize('NFKD', str(texto))
    texto = ''.join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.casefold().strip()
    texto = re.sub(r'[^a-z0-9]+', '_', texto)
    texto = re.sub(r'_+', '_', texto).strip('_')
    return texto


_RUTAS_NORMALIZADAS: dict[str, str] = {
    _normalizar_nombre(carpeta): carpeta
    for carpeta in RUTAS
}
for alias, canonica in ALIAS_CARPETAS.items():
    _RUTAS_NORMALIZADAS[_normalizar_nombre(alias)] = canonica


def _resolver_carpeta_canonica(nombre_carpeta: str) -> str | None:
    return _RUTAS_NORMALIZADAS.get(_normalizar_nombre(nombre_carpeta))


def _inferir_carpeta_por_archivo(nombre_archivo: str) -> str | None:
    """
    Infere carpeta destino cuando el Excel se deja suelto en data/entrada.
    """
    token = _normalizar_nombre(Path(nombre_archivo).stem)
    if not token:
        return None

    for alias, canonica in ALIAS_ARCHIVOS.items():
        if _normalizar_nombre(alias) in token:
            return canonica

    candidatos = sorted(
        ((_normalizar_nombre(carpeta), carpeta) for carpeta in RUTAS),
        key=lambda item: len(item[0]),
        reverse=True
    )
    for clave, canonica in candidatos:
        if clave and clave in token:
            return canonica
    return None


def obtener_archivo_mas_reciente(carpeta: Path) -> Path | None:
    """
    Retorna el archivo .xlsx más reciente de una carpeta.
    Si no hay archivos, retorna None.
    """
    archivos = sorted(
        (
            archivo
            for archivo in carpeta.glob('*.xlsx')
            if not _archivo_tiene_marca_vigente(archivo)
        ),
        key=lambda archivo: archivo.stat().st_mtime,
        reverse=True
    )
    return archivos[0] if archivos else None


def _ruta_marca_archivo(ruta_archivo: Path) -> Path:
    return ruta_archivo.with_name(f'{ruta_archivo.name}.procesado.json')


def _archivo_tiene_marca_vigente(ruta_archivo: Path) -> bool:
    ruta_marca = _ruta_marca_archivo(ruta_archivo)
    if not ruta_marca.exists():
        return False

    try:
        payload = json.loads(ruta_marca.read_text(encoding='utf-8'))
        stat_actual = ruta_archivo.stat()
    except Exception:
        return False

    return (
        int(payload.get('tamano_bytes', -1)) == int(stat_actual.st_size)
        and int(payload.get('mtime_ns', -1)) == int(stat_actual.st_mtime_ns)
        and str(payload.get('estado', '')).upper() in {'PROCESADO', 'RECHAZADO'}
    )


def listar_carpetas_con_archivos() -> list[tuple[str, Path, str]]:
    """
    Recorre CARPETA_ENTRADA y retorna solo las carpetas
    que tienen al menos un archivo .xlsx pendiente.

    Retorna lista de tuplas: (nombre_carpeta, ruta_archivo, tabla_destino)
    """
    pendientes_por_carpeta: dict[str, Path] = {}

    if CARPETA_ENTRADA.exists():
        # 1) Subcarpetas (acepta tildes, mayusculas y separadores distintos).
        for ruta in CARPETA_ENTRADA.iterdir():
            if not ruta.is_dir():
                continue

            carpeta_canonica = _resolver_carpeta_canonica(ruta.name)
            if not carpeta_canonica:
                continue

            archivo = obtener_archivo_mas_reciente(ruta)
            if not archivo:
                continue

            actual = pendientes_por_carpeta.get(carpeta_canonica)
            if actual is None or archivo.stat().st_mtime > actual.stat().st_mtime:
                pendientes_por_carpeta[carpeta_canonica] = archivo

        # 2) Archivos sueltos en data/entrada.
        for archivo in CARPETA_ENTRADA.glob('*.xlsx'):
            if _archivo_tiene_marca_vigente(archivo):
                continue

            carpeta_canonica = _inferir_carpeta_por_archivo(archivo.name)
            if not carpeta_canonica:
                continue

            actual = pendientes_por_carpeta.get(carpeta_canonica)
            if actual is None or archivo.stat().st_mtime > actual.stat().st_mtime:
                pendientes_por_carpeta[carpeta_canonica] = archivo

    pendientes: list[tuple[str, Path, str]] = []
    for carpeta_canonica, tabla_destino in RUTAS.items():
        archivo = pendientes_por_carpeta.get(carpeta_canonica)
        if archivo:
            pendientes.append((carpeta_canonica, archivo, tabla_destino))

    return pendientes


def crear_estructura_carpetas() -> None:
    """
    Crea las carpetas de entrada y procesados si no existen.
    Se llama una sola vez al inicializar el proyecto.
    """
    for nombre_carpeta in RUTAS:
        (CARPETA_ENTRADA / nombre_carpeta).mkdir(parents=True, exist_ok=True)
        (CARPETA_PROCESADOS / nombre_carpeta).mkdir(parents=True, exist_ok=True)
        (CARPETA_RECHAZADOS / nombre_carpeta).mkdir(parents=True, exist_ok=True)

    print(f'Estructura de carpetas creada en: {CARPETA_ENTRADA}')
