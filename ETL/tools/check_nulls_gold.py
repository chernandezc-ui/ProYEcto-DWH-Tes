import sys
import os
import pandas as pd

# Add project directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.conexion import obtener_engine
from sqlalchemy import text

def check_nulls_gold():
    engine = obtener_engine()
    # Get all fact tables in Gold schema
    query_tables = """
    SELECT TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = 'Gold' AND TABLE_NAME LIKE 'Fact_%'
    """
    with engine.connect() as conn:
        tables = [row[0] for row in conn.execute(text(query_tables)).fetchall()]
        for table in tables:
            print("\n" + "=" * 50)
            print(f"AUDITORIA: Gold.{table}")
            print("=" * 50)
            total_rows = conn.execute(text(f"SELECT COUNT(*) FROM Gold.[{table}]")).scalar()
            print(f"Total de registros: {total_rows}")
            if total_rows == 0:
                print("Tabla vacía.")
                continue
            # Get columns
            query_columns = f"""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'Gold' AND TABLE_NAME = '{table}'
            """
            columns = [row[0] for row in conn.execute(text(query_columns)).fetchall()]
            for col in columns:
                null_count = conn.execute(text(f"SELECT COUNT(*) FROM Gold.[{table}] WHERE [{col}] IS NULL")).scalar()
                null_pct = (null_count / total_rows) * 100 if total_rows else 0
                if null_count > 0:
                    print(f"  [!] {col}: {null_count} nulos ({null_pct:.2f}%)")
                else:
                    print(f"  [OK] {col}: 0 nulos (100% completo)")

if __name__ == '__main__':
    check_nulls_gold()
