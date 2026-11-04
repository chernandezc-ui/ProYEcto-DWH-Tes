import sys
import os
import pandas as pd

# Añadir el directorio actual al path para poder importar módulos de la app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.conexion import obtener_engine
from sqlalchemy import text

def check_nulls():
    engine = obtener_engine()
    
    # Obtener todas las tablas fact en Silver
    query_tables = """
    SELECT TABLE_NAME 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME LIKE 'Fact_%'
    """
    
    with engine.connect() as conn:
        tables = [row[0] for row in conn.execute(text(query_tables)).fetchall()]
        
        for table in tables:
            print(f"\\n{'='*50}")
            print(f"AUDITORIA: Silver.{table}")
            print(f"{'='*50}")
            
            # Obtener conteo total
            total_rows = conn.execute(text(f"SELECT COUNT(*) FROM Silver.[{table}]")).scalar()
            print(f"Total de registros: {total_rows}")
            
            if total_rows == 0:
                print("Tabla vacía.")
                continue
                
            # Obtener columnas
            query_columns = f"""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME = '{table}'
            """
            columns = [row[0] for row in conn.execute(text(query_columns)).fetchall()]
            
            for col in columns:
                null_count = conn.execute(text(f"SELECT COUNT(*) FROM Silver.[{table}] WHERE [{col}] IS NULL")).scalar()
                null_pct = (null_count / total_rows) * 100
                if null_count > 0:
                    print(f"  [!] {col}: {null_count} nulos ({null_pct:.2f}%)")
                else:
                    print(f"  [OK] {col}: 0 nulos (100% completo)")

if __name__ == '__main__':
    check_nulls()
