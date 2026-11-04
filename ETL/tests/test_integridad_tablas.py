import sys
import os
from pathlib import Path
import pandas as pd
from sqlalchemy import text

# Agregamos la ruta principal del proyecto al sys.path para poder importar comun
_DIR_PROYECTO = Path(__file__).resolve().parents[2]
if str(_DIR_PROYECTO) not in sys.path:
    sys.path.insert(0, str(_DIR_PROYECTO))

from comun.conexion import obtener_engine

def verificar_tablas():
    engine = obtener_engine()
    
    query_tables = """
    SELECT TABLE_SCHEMA, TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE = 'BASE TABLE'
    """
    
    print("Obteniendo lista de tablas...")
    with engine.connect() as conn:
        tables = conn.execute(text(query_tables)).fetchall()
        
    resultados = []
    
    # Excluimos esquemas de sistema comunes en SQL Server
    esquemas_sistema = [
        'sys', 'INFORMATION_SCHEMA', 'guest', 'db_accessadmin', 
        'db_backupoperator', 'db_datareader', 'db_datawriter', 
        'db_ddladmin', 'db_denydatareader', 'db_denydatawriter', 
        'db_owner', 'db_securityadmin'
    ]
    
    print(f"Se encontraron {len(tables)} tablas en total.")
    
    for schema, table_name in tables:
        if schema in esquemas_sistema:
            continue
            
        fqn = f"[{schema}].[{table_name}]"
        # print(f"Probando {fqn}...")
        
        # 1. Verificar si la tabla puede ser leída y contar registros
        try:
            with engine.connect() as conn:
                count_res = conn.execute(text(f"SELECT COUNT(*) FROM {fqn}")).scalar()
        except Exception as e:
            resultados.append({
                "schema": schema,
                "table": table_name,
                "error_tipo": "Lectura Fallida",
                "detalle": str(e)
            })
            continue
            
        if count_res == 0:
            resultados.append({
                "schema": schema,
                "table": table_name,
                "error_tipo": "Tabla Vacia",
                "detalle": "La tabla tiene 0 registros."
            })
            continue # Si esta vacía, no tiene sentido buscar nulos
            
        # 2. Verificar Nulos en columnas clave (IDs) o similares
        try:
            with engine.connect() as conn:
                cols_query = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table_name}'"
                cols = conn.execute(text(cols_query)).fetchall()
                
            # Columnas que contienen 'id' o 'key'
            id_cols = [c[0] for c in cols if 'id' in c[0].lower() or 'key' in c[0].lower()]
            
            for col in id_cols:
                with engine.connect() as conn:
                    # Validar si hay registros nulos en la columna id
                    null_query = f"SELECT COUNT(*) FROM {fqn} WHERE [{col}] IS NULL"
                    null_count = conn.execute(text(null_query)).scalar()
                    
                    if null_count > 0:
                        resultados.append({
                            "schema": schema,
                            "table": table_name,
                            "error_tipo": "Clave Nula",
                            "detalle": f"La columna clave [{col}] tiene {null_count} registros nulos."
                        })
        except Exception as e:
            print(f"Error revisando nulos en {fqn}: {e}")
            
    # Generar Reporte / Dataset
    df = pd.DataFrame(resultados)
    out_path = Path(__file__).parent / "dataset_errores_integridad.csv"
    
    print("\n================== RESUMEN ==================")
    if not df.empty:
        df.to_csv(out_path, index=False)
        print(f"Se encontraron {len(df)} problemas de integridad.")
        print(f"Dataset generado y guardado en: {out_path}")
        print("\nPrimeros 20 errores detectados:")
        print(df.head(20).to_string())
    else:
        print("¡Todo excelente! No se encontraron tablas vacías ni claves nulas en la validación.")
        
if __name__ == "__main__":
    verificar_tablas()
