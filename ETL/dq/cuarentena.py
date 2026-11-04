"""
cuarentena.py
=============
Envía filas rechazadas por DQ a MDM.Cuarentena.
Toda fila que no pasa validación llega aquí con su motivo.
"""

from datetime import datetime
from sqlalchemy import text

from utils.contexto_transaccional import RecursoDB, administrar_recurso_db
from utils.sql_lotes import TAM_LOTE_DEFECTO


def _normalizar_payload_cuarentena(tabla_origen: str, fila: dict, fecha_ingreso: datetime) -> dict:
    motivo_raw = str(fila.get('motivo', 'Sin motivo') or 'Sin motivo')
    tipo_regla_raw = str(fila.get('tipo_regla', 'DQ') or 'DQ')
    tabla_raw = str(tabla_origen or 'DESCONOCIDA')
    campo_raw = str(fila.get('columna', 'DESCONOCIDA') or 'DESCONOCIDA')
    valor_raw = str(fila.get('valor', '') or '')

    return {
        'tabla_origen': tabla_raw[:100],
        'campo_origen': campo_raw[:100],
        'valor_recibido': valor_raw[:500],
        'motivo': (motivo_raw[:197] + '...') if len(motivo_raw) > 200 else motivo_raw,
        'tipo_regla': tipo_regla_raw[:20],
        'score': fila.get('score_levenshtein', None),
        'id_registro_origen': fila.get('id_registro_origen', None),
        'fecha_ingreso': fecha_ingreso,
    }


def _clave_dedupe_pendiente(payload: dict) -> tuple:
    return (
        payload['tabla_origen'],
        payload['campo_origen'],
        payload['valor_recibido'],
        payload['motivo'],
        payload['id_registro_origen'],
    )


def _deduplicar_payload_pendiente(payload: list[dict]) -> list[dict]:
    deduplicados = []
    vistos = set()
    for fila in payload:
        clave = _clave_dedupe_pendiente(fila)
        if clave in vistos:
            continue
        vistos.add(clave)
        deduplicados.append(fila)
    return deduplicados


def enviar_a_cuarentena(
    recurso_db: RecursoDB,
    tabla_origen: str,
    filas: list[dict],
) -> int:
    """
    Inserta filas rechazadas en MDM.Cuarentena de forma masiva (BULK).
    Retorna el número de filas enviadas.
    """
    if not filas:
        return 0

    ahora = datetime.now()
    payload = _deduplicar_payload_pendiente([
        _normalizar_payload_cuarentena(tabla_origen, fila, ahora)
        for fila in filas
    ])

    with administrar_recurso_db(recurso_db) as conexion:
        # 1. Crear tabla temporal para el batch de errores
        nombre_temp = "#Temp_Quarantine_Load"
        conexion.execute(text(f"IF OBJECT_ID('tempdb..{nombre_temp}') IS NOT NULL DROP TABLE {nombre_temp}"))
        conexion.execute(text(f"""
            CREATE TABLE {nombre_temp} (
                tabla_origen NVARCHAR(255),
                campo_origen NVARCHAR(255),
                valor_recibido NVARCHAR(500),
                motivo NVARCHAR(200),
                tipo_regla NVARCHAR(100),
                score FLOAT,
                id_registro_origen BIGINT,
                fecha_ingreso DATETIME2
            )
        """))

        # 2. Carga masiva a la tabla temporal
        cols = ['tabla_origen','campo_origen','valor_recibido','motivo','tipo_regla','score','id_registro_origen','fecha_ingreso']
        datos = [
            (f['tabla_origen'], f['campo_origen'], f['valor_recibido'], f['motivo'], f['tipo_regla'], f['score'], f['id_registro_origen'], f['fecha_ingreso'])
            for f in payload
        ]
        
        # fast_executemany = False para evitar MemoryError con columnas NVARCHAR
        # (pyodbc pre-aloca ~2GB por NVARCHAR(MAX) por fila cuando fast_executemany=True)
        raw_conn = conexion.connection.dbapi_connection
        cursor = raw_conn.cursor()
        cursor.fast_executemany = False
        sql_temp = f"INSERT INTO {nombre_temp} ({','.join(cols)}) VALUES ({','.join(['?' for _ in cols])})"
        try:
            TAM_LOTE = 5_000
            for inicio in range(0, len(datos), TAM_LOTE):
                lote = datos[inicio : inicio + TAM_LOTE]
                cursor.executemany(sql_temp, lote)
        finally:
            cursor.close()

        # 3. Inserción final en MDM.Cuarentena con filtrado de duplicados PENDIENTES
        sql_final = text(f"""
            INSERT INTO MDM.Cuarentena (
                Tabla_Origen, Campo_Origen, Valor_Recibido, Motivo, 
                Tipo_Regla, Score_Levenshtein, Estado, ID_Registro_Origen, Fecha_Ingreso
            )
            SELECT 
                tmp.tabla_origen, tmp.campo_origen, tmp.valor_recibido, tmp.motivo,
                tmp.tipo_regla, tmp.score, 'PENDIENTE', tmp.id_registro_origen, tmp.fecha_ingreso
            FROM {nombre_temp} tmp
            WHERE NOT EXISTS (
                SELECT 1 FROM MDM.Cuarentena q
                WHERE q.Tabla_Origen = tmp.tabla_origen
                  AND q.Campo_Origen = tmp.campo_origen
                  AND ISNULL(q.Valor_Recibido,'') = ISNULL(tmp.valor_recibido,'')
                  AND q.Motivo = tmp.motivo
                  AND q.Estado = 'PENDIENTE'
                  AND (
                        q.ID_Registro_Origen = tmp.id_registro_origen
                        OR (q.ID_Registro_Origen IS NULL AND tmp.id_registro_origen IS NULL)
                  )
            )
        """)
        resultado = conexion.execute(sql_final)
        total = int(resultado.rowcount or 0)

        # 4. Limpieza
        conexion.execute(text(f"IF OBJECT_ID('tempdb..{nombre_temp}') IS NOT NULL DROP TABLE {nombre_temp}"))

    return total
