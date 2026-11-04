"""
log.py
======
Registro de auditoria del pipeline.
Todo INSERT exitoso o fallido queda registrado en Auditoria.Log_Carga.
Las tablas de auditoria son append-only - sin UPDATE ni DELETE.
"""

from datetime import datetime
from functools import lru_cache

from sqlalchemy import text

from config.conexion import obtener_engine


# Mapeo de claves lógicas a nombres de columnas SQL Server.
# Soporta múltiples esquemas/versiones de la tabla para compatibilidad backward.
COLUMNAS_COMPATIBLES = {
    'estado': ('Estado', 'Estado_Proceso'),
    'archivo': ('Nombre_Archivo', 'Nombre_Archivo_Fuente'),
    'nombre_proceso': ('Nombre_Proceso',),
    'filas_cuarentena': ('Filas_Cuarentena',),
}


@lru_cache(maxsize=1)
def _obtener_columnas_log_carga_cached() -> frozenset[str]:
    """Columnas de Auditoria.Log_Carga. Se cachea — no cambia en producción."""
    with obtener_engine().connect() as con:
        filas = con.execute(text(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = 'Auditoria' AND TABLE_NAME = 'Log_Carga'"
        )).fetchall()
        return frozenset(r[0] for r in filas)


def _resolver_columna(columnas_disponibles: set[str], clave: str) -> str | None:
    for candidata in COLUMNAS_COMPATIBLES[clave]:
        if candidata in columnas_disponibles:
            return candidata
    return None


def registrar_inicio(tabla_destino: str, nombre_archivo: str) -> int:
    engine = obtener_engine()
    columnas = _obtener_columnas_log_carga_cached()

    with engine.begin() as conexion:
        columna_estado = _resolver_columna(columnas, 'estado')
        columna_archivo = _resolver_columna(columnas, 'archivo')
        columna_nombre_proceso = _resolver_columna(columnas, 'nombre_proceso')
        columna_filas_cuarentena = _resolver_columna(columnas, 'filas_cuarentena')

        columnas_insert = ['Tabla_Destino']
        valores_insert = [':tabla_destino']

        if columna_nombre_proceso:
            columnas_insert.append(columna_nombre_proceso)
            valores_insert.append(':nombre_proceso')
        if columna_archivo:
            columnas_insert.append(columna_archivo)
            valores_insert.append(':nombre_archivo')

        columnas_insert.extend([
            'Fecha_Inicio',
            columna_estado,
            'Filas_Leidas',
            'Filas_Insertadas',
            'Filas_Rechazadas',
            'Duracion_Segundos',
            'Mensaje_Error',
        ])
        valores_insert.extend([
            ':fecha_inicio',
            "'EN_PROCESO'",
            '0',
            '0',
            '0',
            '0',
            'NULL',
        ])

        if columna_filas_cuarentena:
            columnas_insert.append(columna_filas_cuarentena)
            valores_insert.append('0')

        sql = f"""
            INSERT INTO Auditoria.Log_Carga (
                {', '.join(columnas_insert)}
            )
            OUTPUT INSERTED.ID_Log_Carga
            VALUES (
                {', '.join(valores_insert)}
            )
        """

        resultado = conexion.execute(text(sql), {
            'tabla_destino': tabla_destino,
            'nombre_proceso': 'ETL_Pipeline',
            'nombre_archivo': nombre_archivo,
            'fecha_inicio': datetime.now(),
        })
        return resultado.fetchone()[0]


def registrar_fin(id_log: int, resultado: dict) -> None:
    engine = obtener_engine()
    fin = datetime.now()
    estado = resultado.get('estado', 'ERROR')
    filas_insertadas = resultado.get('filas', 0)
    filas_rechazadas = resultado.get('rechazadas', 0)
    filas_cuarentena = resultado.get('cuarentena', 0)
    filas_leidas = resultado.get('filas_leidas', filas_insertadas + filas_rechazadas)
    mensaje = resultado.get('mensaje', '')

    columnas = _obtener_columnas_log_carga_cached()

    with engine.begin() as conexion:
        columna_estado = _resolver_columna(columnas, 'estado')
        columna_filas_cuarentena = _resolver_columna(columnas, 'filas_cuarentena')

        asignaciones = [
            'Fecha_Fin = :fecha_fin',
            f'{columna_estado} = :estado',
            'Filas_Leidas = :filas_leidas',
            'Filas_Insertadas = :filas_insertadas',
            'Filas_Rechazadas = :filas_rechazadas',
            'Duracion_Segundos = DATEDIFF(SECOND, Fecha_Inicio, :fecha_fin)',
            'Mensaje_Error = :mensaje_error',
        ]
        if columna_filas_cuarentena:
            asignaciones.append(f'{columna_filas_cuarentena} = :filas_cuarentena')

        sql = f"""
            UPDATE Auditoria.Log_Carga
            SET
                {', '.join(asignaciones)}
            WHERE ID_Log_Carga = :id_log
        """

        conexion.execute(text(sql), {
            'fecha_fin': fin,
            'estado': estado,
            'filas_leidas': filas_leidas,
            'filas_insertadas': filas_insertadas if estado == 'OK' else 0,
            'filas_rechazadas': filas_rechazadas,
            'filas_cuarentena': filas_cuarentena,
            'mensaje_error': mensaje if estado != 'OK' else None,
            'id_log': id_log,
        })


def registrar_decision_mdm(
    tabla_origen: str,
    texto_crudo: str,
    valor_canonico: str,
    decision: str,
    analista_dni: str,
    comentario: str = '',
) -> None:
    engine = obtener_engine()

    with engine.begin() as conexion:
        conexion.execute(text("""
            INSERT INTO Auditoria.Log_Decisiones_MDM (
                Tabla_Origen,
                Texto_Crudo,
                Valor_Canonico,
                Decision,
                Analista_DNI,
                Comentario,
                Fecha_Decision
            ) VALUES (
                :tabla_origen,
                :texto_crudo,
                :valor_canonico,
                :decision,
                :analista_dni,
                :comentario,
                :fecha_decision
            )
        """), {
            'tabla_origen': tabla_origen,
            'texto_crudo': texto_crudo,
            'valor_canonico': valor_canonico,
            'decision': decision,
            'analista_dni': analista_dni,
            'comentario': comentario,
            'fecha_decision': datetime.now(),
        })


def obtener_ultimo_estado(tabla_destino: str) -> dict | None:
    engine = obtener_engine()

    columnas = _obtener_columnas_log_carga_cached()

    with engine.connect() as conexion:
        columna_estado = _resolver_columna(columnas, 'estado')
        columna_filas_cuarentena = _resolver_columna(columnas, 'filas_cuarentena')
        seleccion = [
            f'{columna_estado} AS Estado',
            'Fecha_Inicio',
            'Fecha_Fin',
            'Filas_Insertadas',
            'Filas_Rechazadas',
            'Duracion_Segundos',
            'Mensaje_Error',
        ]
        if columna_filas_cuarentena:
            seleccion.insert(4, f'{columna_filas_cuarentena} AS Filas_Cuarentena')

        resultado = conexion.execute(text(f"""
            SELECT TOP 1
                {', '.join(seleccion)}
            FROM Auditoria.Log_Carga
            WHERE Tabla_Destino = :tabla_destino
            ORDER BY Fecha_Inicio DESC
        """), {'tabla_destino': tabla_destino})

        fila = resultado.fetchone()
        if not fila:
            return None

        return dict(fila._mapping)
