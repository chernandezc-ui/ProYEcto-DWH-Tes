"""
lookup.py
=========
Lookup de IDs de dimensiones desde Silver y MDM.
Cache en memoria — sin consultas por fila.
Surrogate -1 garantizado para Personal sin DNI.
"""

import threading
from typing import Any

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text
import logging
import re
from utils.texto import normalizar_espacio, normalizar_componente_geografico

_log = logging.getLogger("ETL_Pipeline")

# Fundo por defecto cuando una fila no trae fundo explícito.
# Single source of truth — aplica a todo fact/dim que pase por resolver_geografia.
FUNDO_DEFECTO = 'ARANDANO ACP'


_cache: dict[str, pd.DataFrame] = {}
_cache_mapas: dict[str, dict] = {}
_cache_config: dict[str, Any] = {} # Nuevo cache para parámetros y reglas
# RLock (re-entrante) en vez de Lock plano: `resolver_geografia` (linea ~645)
# envuelve toda su logica en `with _cache_lock:` para atomicidad, pero dentro
# llama funciones (`_cargar_reglas_mdm`, `_obtener_id_catalogo`, etc.) que
# tambien hacen `with _cache_lock:`. Con Lock no-reentrante, el mismo thread
# se bloqueaba esperandose a si mismo -> deadlock en cada fila al construir
# payload de cualquier Fact. RLock permite re-entrada del MISMO thread sin
# romper la atomicidad frente a otros threads (mantiene la garantia).
_cache_lock = threading.RLock()

_ALIASES_CINTA = {
    'amarillo': 'amarilla',
    'blanco': 'blanca',
    'rojo': 'roja',
}

# Aliases para Dim_Estado_Fenologico: mapea variantes de texto de campo
# Categoria → Nombre_Estado canónico (case-insensitive, ya normalizado).
_ALIASES_ESTADO_FENOLOGICO = {
    'ffase1':          'inicio f1',
    'ffase2':          'inicio f2',
    'inicio fase 1':   'inicio f1',
    'inicio fase 2':   'inicio f2',
    'cosecha':         'cosechable',
    'floracion':       'flor',
    'floración':       'flor',
    'pequena':         'pequena',
    'pequeña':         'pequena',
    'punta verde':     'verde',
    'yema':            'yema hinchada',
}


def obtener_parametros_pipeline(engine: Engine) -> dict[str, Any]:
    """Carga parámetros generales desde Config.Parametros_Pipeline."""
    with _cache_lock:
        if 'parametros_pipeline' not in _cache_config:
            with engine.connect() as conexion:
                resultado = conexion.execute(text("SELECT Nombre_Parametro, Valor FROM Config.Parametros_Pipeline"))
                _cache_config['parametros_pipeline'] = {row[0]: row[1] for row in resultado}
        return _cache_config['parametros_pipeline']


def obtener_reglas_validacion(engine: Engine) -> pd.DataFrame:
    """Carga reglas de validación específicas desde Config.Reglas_Validacion."""
    with _cache_lock:
        if 'reglas_validacion' not in _cache_config:
            with engine.connect() as conexion:
                resultado = conexion.execute(text("SELECT * FROM Config.Reglas_Validacion WHERE Activo = 1"))
                _cache_config['reglas_validacion'] = pd.DataFrame(resultado.fetchall(), columns=resultado.keys())
        return _cache_config['reglas_validacion']


def _cargar_dim(engine: Engine, tabla: str,
                col_id: str, col_clave: str) -> pd.DataFrame:
    # Cache key incluye col_clave: la misma tabla se consulta con distintas
    # columnas (ej. Dim_Personal por DNI y por Nombre_Completo). Cachear solo
    # por tabla devolvia un DataFrame con la columna equivocada -> KeyError.
    clave_cache = f'{tabla}::{col_id}::{col_clave}'
    with _cache_lock:
        if clave_cache not in _cache:
            with engine.connect() as conexion:
                resultado = conexion.execute(
                    text(f'SELECT {col_id}, {col_clave} FROM {tabla} WITH (NOLOCK)')
                )
                _cache[clave_cache] = pd.DataFrame(
                    resultado.fetchall(), columns=[col_id, col_clave]
                )
        return _cache[clave_cache]


def limpiar_cache() -> None:
    """
    Vacía todos los caches de dimensiones y mapas.

    CONTRATO: debe llamarse al inicio de cada corrida del pipeline
    (pipeline.ejecutar() y pipeline.ejecutar_reproceso_facts() ya lo hacen).
    Si no se llama entre corridas en el mismo proceso (ej. FastAPI con múltiples
    ejecuciones), el cache puede devolver IDs de una corrida anterior si se
    insertaron nuevas dimensiones en Silver entre medias.
    """
    with _cache_lock:
        n_dims = len(_cache)
        n_mapas = len(_cache_mapas)
        _cache.clear()
        _cache_mapas.clear()
    if n_dims or n_mapas:
        _log.debug(f'Cache de lookup limpiado: {n_dims} dims, {n_mapas} mapas descartados.')



def _normalizar_texto(valor) -> str | None:
    t = normalizar_espacio(valor)
    return t.lower() if t else None


def _geo_nombre_token(valor) -> str | None:
    """Los nombres de fundo/sector conservan letras y números completos.

    La normalización operativa convertiría 'Fundo 2 Norte' y 'Fundo 2 Sur'
    al mismo token '2'. Solo módulo/turno/válvula/cama admiten esa reducción.
    """
    if valor is None or pd.isna(valor):
        return None
    texto = normalizar_espacio(str(valor))
    if not texto or texto.casefold() in ('none', 'nan', 'null'):
        return None
    return texto.casefold()


def _normalizar_componente(valor) -> str:
    t = normalizar_componente_geografico(valor)
    if t is None or t.upper() in ('NONE', 'NAN', 'NULL', 'SIN_FUNDO', 'SIN_SECTOR', 'SIN_MODULO', 'SIN_TURNO', 'SIN_VALVULA', 'SIN_CAMA'):
        return 'NONE'
    return t.lower()


_RE_GEO_LIMPIEZA = re.compile(r'[+-]?\d+\.*0*')

def _geo_token(valor) -> str | None:
    if valor is None:
        return None
    if isinstance(valor, float) and pd.isna(valor):
        return None

    texto = normalizar_componente_geografico(str(valor))
    if not texto or texto.lower() in ('', 'none', 'nan'):
        return None

    try:
        if _RE_GEO_LIMPIEZA.fullmatch(texto):
            return str(int(float(texto)))
    except:
        pass

    return str(texto).lower()


def _obtener_mapa_dim(engine: Engine,
                      tabla: str,
                      col_id: str,
                      col_clave: str) -> dict[str, int]:
    clave_cache = f'mapa::{tabla}::{col_id}::{col_clave}'
    with _cache_lock:
        if clave_cache in _cache_mapas:
            return _cache_mapas[clave_cache]

    dim = _cargar_dim(engine, tabla, col_id, col_clave)
    # Optimización: usar set_index y to_dict en lugar de iterrows
    df_map = dim.copy()
    df_map['clave_norm'] = df_map[col_clave].map(_normalizar_texto)
    df_map = df_map.dropna(subset=['clave_norm'])
    
    mapa = df_map.set_index('clave_norm')[col_id].to_dict()

    with _cache_lock:
        _cache_mapas[clave_cache] = mapa
    return mapa


def obtener_id_tiempo(fecha_yyyymmdd: int | None,
                       engine: Engine) -> int | None:
    if fecha_yyyymmdd is None:
        return None
    try:
        clave = str(int(fecha_yyyymmdd))
    except (ValueError, TypeError):
        return None

    clave_cache = 'mapa::Silver.Dim_Tiempo::ID_Tiempo'
    with _cache_lock:
        if clave_cache not in _cache_mapas:
            with engine.connect() as conexion:
                resultado = conexion.execute(text("""
                    SELECT ID_Tiempo
                    FROM Silver.Dim_Tiempo WITH (NOLOCK)
                """))
                mapa = {}
                for fila in resultado.fetchall():
                    try:
                        id_tiempo = int(fila[0])
                        mapa[str(id_tiempo)] = id_tiempo
                    except (ValueError, TypeError):
                        continue
                _cache_mapas[clave_cache] = mapa

    with _cache_lock:
        mapa = _cache_mapas[clave_cache]
    return mapa.get(clave)


def obtener_id_variedad(nombre_canonico: str | None,
                         engine: Engine) -> int | None:
    clave = _normalizar_texto(nombre_canonico)
    if clave is None:
        return None
    mapa = _obtener_mapa_dim(engine, 'Silver.Dim_Variedad', 'ID_Variedad', 'Nombre_Variedad')
    return mapa.get(clave)


def resolver_variedades_batch(lista_canonicas: list[str | None],
                               engine: Engine) -> dict[str, int | None]:
    """
    Resuelve una lista de nombres canónicos a sus IDs de dimensión en una sola operación.
    """
    mapa_dim = _obtener_mapa_dim(engine, 'Silver.Dim_Variedad', 'ID_Variedad', 'Nombre_Variedad')
    
    resultado: dict[str, int | None] = {}
    for nombre in lista_canonicas:
        if nombre is None:
            continue
        clave = _normalizar_texto(nombre)
        resultado[nombre] = mapa_dim.get(clave) if clave else None
        
    return resultado


def obtener_id_personal(identificador: str | None,
                          engine: Engine) -> int:
    """
    Resuelve ID_Personal buscando primero por DNI y luego por Nombre_Completo.
    Retorna -1 (surrogate 'Sin Evaluador') si no se resuelve.
    """
    if identificador is None:
        return -1
    
    clave = _normalizar_texto(identificador)
    if clave is None:
        return -1

    # 1. Intentar por DNI
    mapa_dni = _obtener_mapa_dim(engine, 'Silver.Dim_Personal', 'ID_Personal', 'DNI')
    if clave in mapa_dni:
        return mapa_dni[clave]

    # 2. Intentar por Nombre_Completo
    mapa_nombre = _obtener_mapa_dim(engine, 'Silver.Dim_Personal', 'ID_Personal', 'Nombre_Completo')
    return mapa_nombre.get(clave, -1)


def _obtener_id_geografia_dim_basica(fundo: str | None,
                                     sector: str | None,
                                     modulo,
                                     engine: Engine) -> int | None:
    """
    Busca ID_Geografia por fundo + sector + modulo.
    Solo retorna registros vigentes (Es_Vigente = 1).

    FIX: si fundo es None pero sector no es None, busca solo por sector.
    Esto cubre Fact_Telemetria_Clima donde el Excel solo trae Sector.
    """
    if not fundo and not sector and modulo is None:
        return None

    clave_cache = 'Silver.Dim_Geografia'
    if clave_cache not in _cache:
        with engine.connect() as conexion:
            resultado = conexion.execute(text("""
                SELECT ID_Geografia, Fundo, Sector, Modulo
                FROM Silver.vDim_Geografia WITH (NOLOCK)
                WHERE Es_Vigente = 1
            """))
            _cache[clave_cache] = pd.DataFrame(
                resultado.fetchall(),
                columns=['ID_Geografia', 'Fundo', 'Sector', 'Modulo']
            )
            
            # O(1) Indexing
            idx = {}
            for _, r in _cache[clave_cache].iterrows():
                k = (str(r['Fundo']).lower(), str(r['Sector']).lower(), str(r['Modulo']).lower())
                idx[k] = int(r['ID_Geografia'])
            _cache_mapas[f'{clave_cache}_idx'] = idx

    with _cache_lock:
        idx = _cache_mapas.get('Silver.Dim_Geografia_idx', {})
        f_key = str(fundo).lower() if fundo else 'none'
        s_key = str(sector).lower() if sector else 'none'
        m_key = str(modulo).lower() if modulo is not None else 'none'
        clave_lookup = (f_key, s_key, m_key)
        
        if clave_lookup in idx:
            return idx[clave_lookup]
            
    # Fallback sector-only (Telemetria)
    if not fundo and sector:
        with _cache_lock:
            dim = _cache['Silver.Dim_Geografia']
            mascara = dim['Sector'].str.lower() == sector.lower()
            if modulo is not None:
                mascara &= dim['Modulo'].astype(str).str.lower() == str(modulo).lower()
            coincidencia = dim[mascara]
            return int(coincidencia.iloc[0]['ID_Geografia']) if not coincidencia.empty else None

    return None


def obtener_id_estado_fenologico(estado: str | None,
                                   engine: Engine) -> int | None:
    clave = _normalizar_texto(estado)
    if clave is None:
        return None
    mapa = _obtener_mapa_dim(
        engine,
        'Silver.Dim_Estado_Fenologico',
        'ID_Estado_Fenologico',
        'Nombre_Estado'
    )
    return mapa.get(clave)


def obtener_id_actividad(actividad: str | None,
                          engine: Engine) -> int | None:
    clave = _normalizar_texto(actividad)
    if clave is None:
        return None
    mapa = _obtener_mapa_dim(
        engine,
        'Silver.Dim_Actividad_Operativa',
        'ID_Actividad',
        'Nombre_Actividad'
    )
    return mapa.get(clave)


def obtener_id_cinta(color: str | None,
                      engine: Engine) -> int | None:
    clave = _normalizar_texto(color)
    if clave is None:
        return None
    mapa = _obtener_mapa_dim(engine, 'Silver.Dim_Cinta', 'ID_Cinta', 'Color_Cinta')
    if clave in mapa:
        return mapa[clave]

    clave_alias = _ALIASES_CINTA.get(clave)
    if clave_alias is not None:
        return mapa.get(clave_alias)

    return None


def obtener_id_estado_fenologico(categoria: str | None,
                                 engine: Engine) -> int | None:
    """Resuelve el texto de Categoria al ID de Silver.Dim_Estado_Fenologico.

    Aplica normalización de texto y aliases para variantes comunes
    (FFase1, FFase2, Cosecha, Floración, etc.).
    Retorna None si la categoría no se puede resolver.
    """
    clave = _normalizar_texto(categoria)
    if clave is None:
        return None
    mapa = _obtener_mapa_dim(
        engine, 'Silver.Dim_Estado_Fenologico',
        'ID_Estado_Fenologico', 'Nombre_Estado'
    )
    # Coincidencia directa
    if clave in mapa:
        return mapa[clave]
    # Alias configurado
    clave_alias = _ALIASES_ESTADO_FENOLOGICO.get(clave)
    if clave_alias is not None:
        return mapa.get(clave_alias)
    return None


def _descomponer_modulo_submodulo_token(modulo_token: str | None) -> tuple[str | None, str | None]:
    if modulo_token is None:
        return None, None

    # Caso 9.1, 9.2, etc.
    coincidencia = re.fullmatch(r'([+-]?\d+)\.(\d+)', modulo_token)
    if coincidencia:
        return coincidencia.group(1), str(int(coincidencia.group(2)))

    return modulo_token, None

def _cargar_reglas_mdm(engine: Engine) -> tuple[pd.DataFrame, pd.DataFrame]:
    with _cache_lock:
        if 'MDM.Regla_Modulo_Raw' not in _cache:
            with engine.connect() as conexion:
                # Reglas simples
                try:
                    res = conexion.execute(text("SELECT Modulo_Raw, Modulo_Int, SubModulo_Int, Es_Test_Block FROM MDM.Regla_Modulo_Raw WITH (NOLOCK) WHERE Es_Activa = 1"))
                    _cache['MDM.Regla_Modulo_Raw'] = pd.DataFrame(res.fetchall(), columns=['Modulo_Raw', 'Modulo_Int', 'SubModulo_Int', 'Es_Test_Block'])
                except:
                    _cache['MDM.Regla_Modulo_Raw'] = pd.DataFrame(columns=['Modulo_Raw', 'Modulo_Int', 'SubModulo_Int', 'Es_Test_Block'])

                # Reglas por rango de turno
                try:
                    res = conexion.execute(text("SELECT Modulo_Raw_Base, Turno_Desde, Turno_Hasta, Modulo_Int, SubModulo_Int, Es_Test_Block FROM MDM.Regla_Modulo_Turno_SubModulo WITH (NOLOCK) WHERE Es_Activa = 1"))
                    _cache['MDM.Regla_Modulo_Turno_SubModulo'] = pd.DataFrame(res.fetchall(), columns=['Modulo_Raw_Base', 'Turno_Desde', 'Turno_Hasta', 'Modulo_Int', 'SubModulo_Int', 'Es_Test_Block'])
                except:
                    _cache['MDM.Regla_Modulo_Turno_SubModulo'] = pd.DataFrame(columns=['Modulo_Raw_Base', 'Turno_Desde', 'Turno_Hasta', 'Modulo_Int', 'SubModulo_Int', 'Es_Test_Block'])
    
        return _cache['MDM.Regla_Modulo_Raw'], _cache['MDM.Regla_Modulo_Turno_SubModulo']

def _cargar_geografia(engine: Engine) -> pd.DataFrame:
    """Carga Dim_Geografia vigente en DataFrame (para backcompat con _obtener_id_geografia_dim_basica)."""
    clave_cache = 'Silver.Dim_Geografia'
    with _cache_lock:
        if clave_cache not in _cache:
            with engine.connect() as conexion:
                resultado = conexion.execute(text("""
                    SELECT
                        ID_Geografia, ID_Fundo_Catalogo, ID_Sector_Catalogo,
                        ID_Modulo_Catalogo, ID_Turno_Catalogo, ID_Valvula_Catalogo,
                        ID_Cama_Catalogo, Es_Test_Block
                    FROM Silver.Dim_Geografia WITH (NOLOCK)
                    WHERE Es_Vigente = 1
                """))
                _cache[clave_cache] = pd.DataFrame(
                    resultado.fetchall(), 
                    columns=[
                        'ID_Geografia', 'ID_Fundo_Catalogo', 'ID_Sector_Catalogo',
                        'ID_Modulo_Catalogo', 'ID_Turno_Catalogo', 'ID_Valvula_Catalogo',
                        'ID_Cama_Catalogo', 'Es_Test_Block'
                    ]
                )
        return _cache[clave_cache]

def _cargar_indice_id_geografia_modulo(engine: Engine) -> dict[int, int]:
    """Retorna un dict O(1) de ID_Geografia -> ID_Modulo_Catalogo"""
    clave_idx = 'geo_indice_id_modulo'
    with _cache_lock:
        if clave_idx in _cache_mapas:
            return _cache_mapas[clave_idx]

    df_geo = _cargar_geografia(engine)
    indice = {}
    for _, fila in df_geo.iterrows():
        indice[int(fila['ID_Geografia'])] = int(fila['ID_Modulo_Catalogo'])

    with _cache_lock:
        _cache_mapas[clave_idx] = indice

    return indice


def _cargar_indice_geografia(engine: Engine) -> dict[tuple, list[dict]]:
    """
    Construye un diccionario indexado por (ID_Modulo, ID_Turno, ID_Valvula)
    para resolución O(1) de geografía. Cada valor es una lista de registros
    que coinciden con esa combinación base.

    Se construye una sola vez y se cachea junto con el DataFrame.
    """
    clave_idx = 'geo_indice_mtv'
    with _cache_lock:
        if clave_idx in _cache_mapas:
            return _cache_mapas[clave_idx]

    df_geo = _cargar_geografia(engine)
    indice: dict[tuple, list[dict]] = {}

    for _, fila in df_geo.iterrows():
        clave = (
            int(fila['ID_Modulo_Catalogo']),
            int(fila['ID_Turno_Catalogo']),
            int(fila['ID_Valvula_Catalogo']),
            int(fila['ID_Cama_Catalogo']),
        )
        registro = {
            'ID_Geografia': int(fila['ID_Geografia']),
            'ID_Fundo_Catalogo': int(fila['ID_Fundo_Catalogo']),
            'ID_Sector_Catalogo': int(fila['ID_Sector_Catalogo']),
            'ID_Modulo_Catalogo': int(fila['ID_Modulo_Catalogo']),
            'Es_Test_Block': int(fila['Es_Test_Block']),
        }
        indice.setdefault(clave, []).append(registro)

    with _cache_lock:
        _cache_mapas[clave_idx] = indice

    return indice

 
def _cargar_bridge_campanas(engine: Engine) -> pd.DataFrame:
    clave_cache = 'Silver.Bridge_Modulo_Campana'
    with _cache_lock:
        if clave_cache not in _cache:
            with engine.connect() as conexion:
                df = pd.read_sql("""
                    SELECT ID_Modulo_Catalogo, ID_Variedad, ID_Campana, Fecha_Inicio, Fecha_Fin 
                    FROM Silver.Bridge_Modulo_Campana WITH (NOLOCK)
                    WHERE Es_Activa = 1
                """, conexion)
                df['Fecha_Inicio'] = pd.to_datetime(df['Fecha_Inicio'])
                # Usar fecha lejana para vigencia activa
                df['Fecha_Fin'] = pd.to_datetime(df['Fecha_Fin'].fillna(pd.Timestamp.max))
                _cache[clave_cache] = df
        return _cache[clave_cache]

def _cargar_indice_bridge_campanas(engine: Engine) -> dict[tuple[int, int], list[dict]]:
    clave_idx = 'campanas_indice_mv'
    with _cache_lock:
        if clave_idx in _cache_mapas:
            return _cache_mapas[clave_idx]

    df_bridge = _cargar_bridge_campanas(engine)
    indice: dict[tuple[int, int], list[dict]] = {}

    for _, fila in df_bridge.iterrows():
        clave = (int(fila['ID_Modulo_Catalogo']), int(fila['ID_Variedad']))
        registro = {
            'ID_Campana': int(fila['ID_Campana']),
            'Fecha_Inicio': fila['Fecha_Inicio'],
            'Fecha_Fin': fila['Fecha_Fin']
        }
        indice.setdefault(clave, []).append(registro)

    # Ordenar por fecha_inicio descendente para facilitar la busqueda de la mas reciente
    for clave in indice:
        indice[clave].sort(key=lambda x: x['Fecha_Inicio'], reverse=True)

    with _cache_lock:
        _cache_mapas[clave_idx] = indice

    return indice

def _obtener_id_catalogo(engine: Engine, tabla: str, col_id: str, col_nombre: str, valor: str | None) -> int:
    """
    Lookup en catalogo independiente. Retorna ID o 0 (Sentinel) si no se resuelve.
    """
    if valor is None:
        return 0
    
    # Normalizacion especifica para catalogos
    normalizar = _geo_nombre_token if col_nombre in ('Fundo', 'Sector') else _normalizar_componente
    clave = normalizar(valor)
    if clave == 'none':
        return 0
    
    # La clave recibida y los nombres del catálogo deben normalizarse igual.
    # El mapa genérico solo normaliza espacios: E2E_A y E2E A no coincidían,
    # y un fundo desconocido quedaba como 0, eliminando el filtro geográfico.
    cache_key = f'catalogo_geo::{tabla}::{col_id}::{col_nombre}'
    with _cache_lock:
        if cache_key not in _cache_mapas:
            df = _cargar_dim(engine, tabla, col_id, col_nombre)
            mapa = {}
            for _, fila in df.iterrows():
                key = normalizar(fila[col_nombre])
                identifier = int(fila[col_id])
                if key in mapa and mapa[key] != identifier:
                    # Un alias normalizado ambiguo no debe elegir el último ID.
                    mapa[key] = 0
                else:
                    mapa[key] = identifier
            _cache_mapas[cache_key] = mapa
        mapa = _cache_mapas[cache_key]
    return mapa.get(clave, 0)

def _resolver_id_geografia_desde_catalogos(engine: Engine, 
                                           id_fundo: int, id_sector: int, id_modulo: int,
                                           id_turno: int, id_valvula: int, id_cama: int) -> dict | None:
    """
    Resuelve ID_Geografia usando búsqueda O(1) en diccionario indexado
    por (ID_Modulo, ID_Turno, ID_Valvula).

    Reemplaza el filtrado por mascara de Pandas que era O(n) por cada fila
    procesada, con un lookup de diccionario que es O(1).
    """
    indice = _cargar_indice_geografia(engine)

    # Busqueda O(1) por la clave base: Modulo, Turno, Valvula, Cama
    clave = (id_modulo, id_turno, id_valvula, id_cama)
    candidatos = indice.get(clave)

    if not candidatos:
        return None

    # Filtrar por Fundo/Sector si se proporcionaron
    if id_fundo > 0 or id_sector > 0:
        filtrados = candidatos
        if id_fundo > 0:
            filtrados = [c for c in filtrados if c['ID_Fundo_Catalogo'] == id_fundo]
        if id_sector > 0:
            filtrados = [c for c in filtrados if c['ID_Sector_Catalogo'] == id_sector]
        candidatos = filtrados

    if not candidatos:
        return None

    if len(candidatos) > 1:
        return {
            'id_geografia': None,
            'id_modulo_catalogo': id_modulo,
            'estado': 'GEOGRAFIA_AMBIGUA',
            'detalle': 'Mas de una geografia vigente coincide; especifique fundo/sector completos.'
        }
    
    reg = candidatos[0]
    return {
        'id_geografia': reg['ID_Geografia'],
        'id_modulo_catalogo': reg['ID_Modulo_Catalogo'],
        'es_test_block': reg['Es_Test_Block'],
        'estado': 'RESUELTA_CATALOGOS',
        'detalle': 'Resuelta corroborando catalogos independientes.'
    }

def _crear_combinacion_geografia(engine: Engine, id_f, id_s, id_m, id_t, id_v, id_c, tb=0) -> int:
    """
    Crea una nueva combinacion en Silver.Dim_Geografia (Auto-Create).
    """
    with engine.begin() as conn:
        res = conn.execute(text("""
            INSERT INTO Silver.Dim_Geografia (
                ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo,
                ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Cama_Catalogo,
                Es_Test_Block, Nivel_Granularidad, Fecha_Inicio_Vigencia, Es_Vigente
            )
            OUTPUT INSERTED.ID_Geografia
            VALUES (:f, :s, :m, :t, :v, :c, :tb, 'AUTO_ETL', GETDATE(), 1)
        """), {"f": id_f, "s": id_s, "m": id_m, "t": id_t, "v": id_v, "c": id_c, "tb": tb})
        new_id = res.scalar()
        # Optimización: En lugar de invalidar el caché destructivamente y forzar
        # a cargar 40K registros desde SQL Server para cada nueva geografía,
        # agregamos la nueva geografía al índice O(1) directamente.
        with _cache_lock:
            if 'geo_indice_mtv' in _cache_mapas:
                clave = (id_m, id_t, id_v, id_c)
                registro = {
                    'ID_Geografia': new_id,
                    'ID_Fundo_Catalogo': id_f,
                    'ID_Sector_Catalogo': id_s,
                    'ID_Modulo_Catalogo': id_m,
                    'Es_Test_Block': tb,
                }
                _cache_mapas['geo_indice_mtv'].setdefault(clave, []).append(registro)
            # Ya no eliminamos _cache['Silver.Dim_Geografia']
        return new_id



def _resolver_id_modulo_catalogo_con_reglas(engine: Engine, modulo_raw: str | None, turno_token: str | None) -> tuple[int, int]:
    """
    Resuelve ID_Modulo_Catalogo y Es_Test_Block usando las reglas de MDM.
    Retorna (id_modulo, es_test_block).
    """
    if modulo_raw is None:
        return 0, 0
    
    reglas_raw, reglas_turno = _cargar_reglas_mdm(engine)
    
    # 1. Regla Simple (Exacta)
    match_raw = reglas_raw[reglas_raw['Modulo_Raw'].str.upper() == modulo_raw.upper()]
    if not match_raw.empty:
        # Resolvemos el Modulo_Int en el catalogo
        id_mod = _resolver_id_modulo_catalogo(engine, str(match_raw.iloc[0]['Modulo_Int']), str(match_raw.iloc[0]['SubModulo_Int']))
        return id_mod, int(match_raw.iloc[0]['Es_Test_Block'])
    
    # 2. Regla por Turno
    if turno_token and turno_token.isdigit():
        t = int(turno_token)
        match_t = reglas_turno[
            (reglas_turno['Modulo_Raw_Base'].str.upper() == modulo_raw.upper()) &
            (reglas_turno['Turno_Desde'] <= t) &
            (reglas_turno['Turno_Hasta'] >= t)
        ]
        if not match_t.empty:
            id_mod = _resolver_id_modulo_catalogo(engine, str(match_t.iloc[0]['Modulo_Int']), str(match_t.iloc[0]['SubModulo_Int']))
            return id_mod, int(match_t.iloc[0]['Es_Test_Block'])

    # 3. Fallback: Modulo directo o descomposicion de Submodulo (ej. 9.1)
    m_base, sub = _descomponer_modulo_submodulo_token(modulo_raw)
    if m_base:
        id_mod = _resolver_id_modulo_catalogo(engine, m_base, sub)
        return id_mod, 0

    return 0, 0

def _resolver_id_modulo_catalogo(engine: Engine, modulo_base: str | None, submodulo: str | None) -> int:
    """
    Resuelve ID_Modulo_Catalogo buscando match exacto en Modulo y SubModulo.
    """
    if modulo_base is None:
        return 0
    
    # Cargamos el catalogo de modulos completo (es pequeño)
    clave_cache = 'mapa::Silver.Dim_Modulo_Catalogo::full'
    with _cache_lock:
        if clave_cache not in _cache_mapas:
            with engine.connect() as conexion:
                resultado = conexion.execute(text("""
                    SELECT ID_Modulo_Catalogo, Modulo, SubModulo 
                    FROM Silver.Dim_Modulo_Catalogo WITH (NOLOCK)
                """))
                df = pd.DataFrame(resultado.fetchall(), columns=['ID', 'Mod', 'Sub'])
                df['Mod_token'] = df['Mod'].map(_geo_token)
                df['Sub_token'] = df['Sub'].map(_geo_token)
                _cache_mapas[clave_cache] = df
    
    df = _cache_mapas[clave_cache]
    
    # Busqueda: Modulo exacto y Submodulo exacto
    modulo_base_token = _geo_token(modulo_base)
    # Submodulo es opcional, si es 0 o None se trata como base
    sub_raw = str(submodulo) if submodulo and str(submodulo).lower() not in ('none', 'nan', '0') else None
    submodulo_token = _geo_token(sub_raw)

    if submodulo_token:
        mascara = (df['Mod_token'] == modulo_base_token) & (df['Sub_token'] == submodulo_token)
    else:
        # Si no hay submodulo en la regla, buscamos registros sin submodulo (NaN o '0')
        mascara = (df['Mod_token'] == modulo_base_token) & (df['Sub_token'].isna() | (df['Sub_token'] == '0'))
    
    coincidencias = df[mascara]
    if not coincidencias.empty:
        return int(coincidencias.iloc[0]['ID'])
    
    return 0


def _es_modulo_especial(modulo_token: str | None) -> bool:
    return modulo_token is None or str(modulo_token).strip() == ''

def registrar_aprendizaje_geografia(engine: Engine, 
                                     fundo: str | None, sector: str | None, modulo: str | None, 
                                     turno: str | None, valvula: str | None, cama: str | None):
    """
    Registra una combinacion desconocida en MDM para que el sistema 'aprenda'.
    No duplica registros si ya estan en MDM esperando validacion.
    """
    with engine.begin() as conn:
        conn.execute(text("""
            IF NOT EXISTS (
                SELECT 1 FROM MDM.Catalogo_Geografia 
                WHERE ISNULL(Fundo,'') = ISNULL(:f,'') AND ISNULL(Sector,'') = ISNULL(:s,'')
                  AND ISNULL(Modulo,'') = ISNULL(:m,'') AND ISNULL(Turno,'') = ISNULL(:t,'')
                  AND ISNULL(Valvula,'') = ISNULL(:v,'') AND ISNULL(Cama,'') = ISNULL(:c,'')
            )
            INSERT INTO MDM.Catalogo_Geografia (Fundo, Sector, Modulo, Turno, Valvula, Cama, Es_Activa, Fecha_Creacion)
            VALUES (:f, :s, :m, :t, :v, :c, 0, GETDATE())
        """), {"f": fundo, "s": sector, "m": modulo, "t": turno, "v": valvula, "c": cama})

def resolver_geografia(fundo: str | None,
                       sector: str | None,
                       modulo,
                       engine: Engine,
                       turno=None,
                       valvula=None,
                       cama=None) -> dict:
    """
    Resolver principal de geografia usando CATALOGOS INDEPENDIENTES.
    Bloqueado globalmente para evitar duplicados en auto-create simultaneo.
    """
    fundo_token = _geo_nombre_token(fundo) or FUNDO_DEFECTO
    sector_token = _geo_nombre_token(sector)
    modulo_token = _geo_token(modulo)
    turno_token = _geo_token(turno)
    valvula_token = _geo_token(valvula)
    cama_token = _geo_token(cama)

    clave_busqueda = (
        fundo_token, sector_token, modulo_token,
        turno_token, valvula_token, cama_token,
    )

    # El lock envuelve TODA la logica de resolucion + creacion para atomicidad
    with _cache_lock:
        mapa_geo = _cache_mapas.setdefault('geo_resolucion_catalogos', {})
        if clave_busqueda in mapa_geo:
            return mapa_geo[clave_busqueda]

        # 1. Aplicar Reglas de MDM para resolver Modulo Canonico
        id_modulo, es_test_block = _resolver_id_modulo_catalogo_con_reglas(engine, modulo_token, turno_token)
        
        # 2. Resolver IDs de Catalogos para el resto de componentes
        id_fundo = _obtener_id_catalogo(engine, 'Silver.Dim_Fundo_Catalogo', 'ID_Fundo_Catalogo', 'Fundo', fundo_token)
        id_sector = _obtener_id_catalogo(engine, 'Silver.Dim_Sector_Catalogo', 'ID_Sector_Catalogo', 'Sector', sector_token)
        id_turno = _obtener_id_catalogo(engine, 'Silver.Dim_Turno_Catalogo', 'ID_Turno_Catalogo', 'Turno', turno_token)
        id_valvula = _obtener_id_catalogo(engine, 'Silver.Dim_Valvula_Catalogo', 'ID_Valvula_Catalogo', 'Valvula', valvula_token)
        id_cama = _obtener_id_catalogo(engine, 'Silver.Dim_Cama_Catalogo', 'ID_Cama_Catalogo', 'Cama_Normalizada', cama_token)

        if id_fundo <= 0 or (sector_token is not None and id_sector <= 0):
            resultado = {
                'id_geografia': None,
                'id_modulo_catalogo': id_modulo,
                'estado': 'PENDIENTE_GEOGRAFIA_NO_EXISTE',
                'detalle': 'Fundo o sector no reconocido en catalogo; no se permite buscar sin ese filtro.'
            }
            mapa_geo[clave_busqueda] = resultado
            return resultado

        # 3. Intentar resolver combinacion en Dim_Geografia
        resultado = _resolver_id_geografia_desde_catalogos(engine, id_fundo, id_sector, id_modulo, id_turno, id_valvula, id_cama)
        
        if resultado:
            mapa_geo[clave_busqueda] = resultado
            return resultado

        # 4. Auto-Create si todos los componentes existen en catalogos
        if id_modulo > 0 and id_fundo >= 0 and id_sector >= 0:
            new_id = _crear_combinacion_geografia(engine, id_fundo, id_sector, id_modulo, id_turno, id_valvula, id_cama, es_test_block)
            resultado = {
                'id_geografia': new_id,
                'id_modulo_catalogo': id_modulo,
                'es_test_block': es_test_block,
                'estado': 'RESUELTA_AUTO_CREATE',
                'detalle': 'Combinacion nueva creada automaticamente (Componentes validos).'
            }
            mapa_geo[clave_busqueda] = resultado
            return resultado

        # 5. Fallback/Aprendizaje
        registrar_aprendizaje_geografia(engine, fundo_token, sector_token, modulo_token, turno_token, valvula_token, cama_token)
        
        resultado = {
            'id_geografia': None,
            'id_modulo_catalogo': id_modulo,
            'estado': 'PENDIENTE_GEOGRAFIA_NO_EXISTE',
            'detalle': f'Geografia incompleta o nueva en catalogos. Enviada a MDM (F_ID={id_fundo} S_ID={id_sector} M_ID={id_modulo})'
        }
        mapa_geo[clave_busqueda] = resultado
        return resultado

def obtener_id_geografia(fundo: str | None,
                         sector: str | None,
                         modulo,
                         engine: Engine,
                         turno=None,
                         valvula=None,
                         cama=None) -> int | None:
    resultado = resolver_geografia(fundo, sector, modulo, engine, turno, valvula, cama)
    return resultado.get('id_geografia')

 
def obtener_id_campana(id_geografia: int | None,
                       id_variedad: int | None,
                       fecha_evento,
                       engine: Engine,
                       id_modulo_catalogo: int | None = None) -> int | None:
    """
    Busca la Campana activa usando Bridge_Modulo_Campana (Cacheado en memoria).
    Si id_geografia es None, intenta usar id_modulo_catalogo (match con Dim_Catalogo*).
    """
    if fecha_evento is None:
        return None
 
    try:
        fecha_dt = pd.to_datetime(fecha_evento)
    except:
        return None
 
    # 1. Obtener ID_Modulo_Catalogo (desde parametro o desde la geografia)
    id_mod_cat = id_modulo_catalogo
    
    if id_mod_cat is None and id_geografia is not None:
        idx_modulos = _cargar_indice_id_geografia_modulo(engine)
        id_mod_cat = idx_modulos.get(id_geografia)
 
    if id_mod_cat is None or id_variedad is None:
        return obtener_id_campana_anual(fecha_dt, engine)
 
    # 2. Buscar en el Bridge (Cacheado). Memoizamos por (modulo, variedad, dia)
    #    para no repetir el filtro pandas sobre TODO el bridge en cada fila.
    clave_campana = (int(id_mod_cat), int(id_variedad), pd.Timestamp(fecha_dt).normalize())
    with _cache_lock:
        mapa_campana = _cache_mapas.setdefault('campana_bridge', {})
        if clave_campana in mapa_campana:
            return mapa_campana[clave_campana]

    indice_campanas = _cargar_indice_bridge_campanas(engine)
    candidatos = indice_campanas.get((id_mod_cat, id_variedad), [])

    resultado = None
    for cand in candidatos:
        if cand['Fecha_Inicio'] <= fecha_dt <= cand['Fecha_Fin']:
            resultado = cand['ID_Campana']
            break  # Ya esta ordenado desc por Fecha_Inicio

    if resultado is None:
        # 3. FALLBACK GLOBAL: si no hay en el Bridge, usamos el año calendario
        resultado = obtener_id_campana_anual(fecha_dt, engine)

    with _cache_lock:
        _cache_mapas['campana_bridge'][clave_campana] = resultado
    return resultado


def obtener_id_campana_anual(fecha_evento, engine: Engine) -> int | None:
    """Retorna la campaña anual (Clase 0) correspondiente al año del evento."""
    try:
        fecha_dt = pd.to_datetime(fecha_evento)
        anio_cal = fecha_dt.year
        
        clave_cache = f'campana_anual::{anio_cal}'
        with _cache_lock:
            if clave_cache in _cache_mapas:
                return _cache_mapas[clave_cache]

        with engine.connect() as conn:
            # Buscamos la campaña anual (no asociada a modulo especifico en el bridge)
            # Generalmente tienen Clase_Campana = 0 o son las unicas para ese año en Dim_Campana
            res_c = conn.execute(text("""
                SELECT TOP 1 ID_Campana 
                FROM Silver.Dim_Campana WITH (NOLOCK)
                WHERE Anio_Cosecha = :a 
                ORDER BY ID_Campana DESC
            """), {"a": anio_cal}).fetchone()
            
            id_c = int(res_c[0]) if res_c else None
            with _cache_lock:
                _cache_mapas[clave_cache] = id_c
            return id_c
    except:
        return None
