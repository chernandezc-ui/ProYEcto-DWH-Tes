import sys
import os
import json
from collections import defaultdict

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.conexion import obtener_engine
from sqlalchemy import text

def is_numeric(sql_type: str) -> bool:
    return any(t in sql_type.upper() for t in ['INT', 'DECIMAL', 'NUMERIC', 'FLOAT', 'REAL', 'MONEY', 'SMALLINT', 'BIGINT', 'DOUBLE'])

def metric_gold_tables():
    engine = obtener_engine()
    results = []
    with engine.connect() as conn:
        # Get all Fact tables in Gold schema
        tables = [row[0] for row in conn.execute(text("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'Gold' AND TABLE_NAME LIKE 'Fact_%'
        """)).fetchall()]
        for table in tables:
            table_info = {'tabla': table, 'total_filas': 0, 'columnas': []}
            total = conn.execute(text(f"SELECT COUNT(*) FROM Gold.[{table}]")).scalar() or 0
            table_info['total_filas'] = total
            if total == 0:
                results.append(table_info)
                continue
            # Get columns and types
            cols = conn.execute(text(f"""
                SELECT COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'Gold' AND TABLE_NAME = '{table}'
            """)).fetchall()
            for col_name, data_type in cols:
                col_stats = {'columna': col_name, 'tipo': data_type}
                # Nulls (should be 0)
                nulls = conn.execute(text(f"SELECT COUNT(*) FROM Gold.[{table}] WHERE [{col_name}] IS NULL")).scalar() or 0
                col_stats['nulos'] = nulls
                # Distinct count
                distinct = conn.execute(text(f"SELECT COUNT(DISTINCT [{col_name}]) FROM Gold.[{table}]")).scalar() or 0
                col_stats['distinct'] = distinct
                # Numeric metrics
                if is_numeric(data_type):
                    min_val = conn.execute(text(f"SELECT MIN([{col_name}]) FROM Gold.[{table}]")).scalar()
                    max_val = conn.execute(text(f"SELECT MAX([{col_name}]) FROM Gold.[{table}]")).scalar()
                    avg_val = conn.execute(text(f"SELECT AVG([{col_name}]) FROM Gold.[{table}]")).scalar()
                    col_stats['min'] = float(min_val) if min_val is not None else None
                    col_stats['max'] = float(max_val) if max_val is not None else None
                    col_stats['avg'] = float(avg_val) if avg_val is not None else None
                table_info['columnas'].append(col_stats)
            results.append(table_info)
    # Print JSON summary
    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    metric_gold_tables()
