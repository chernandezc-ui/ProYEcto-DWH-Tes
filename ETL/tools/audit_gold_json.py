import sys
import os
import json
from collections import defaultdict

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.conexion import obtener_engine
from sqlalchemy import text

def audit_gold_nulls():
    engine = obtener_engine()
    issues = []
    # Get all Fact tables in Gold schema
    query_tables = """
    SELECT TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = 'Gold' AND TABLE_NAME LIKE 'Fact_%'
    """
    with engine.connect() as conn:
        tables = [row[0] for row in conn.execute(text(query_tables)).fetchall()]
        for table in tables:
            total = conn.execute(text(f"SELECT COUNT(*) FROM Gold.[{table}]")).scalar() or 0
            if total == 0:
                continue
            # Get columns
            cols = [row[0] for row in conn.execute(text(f"""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'Gold' AND TABLE_NAME = '{table}'
            """)).fetchall()]
            for col in cols:
                nulls = conn.execute(text(f"SELECT COUNT(*) FROM Gold.[{table}] WHERE [{col}] IS NULL")).scalar() or 0
                if nulls > 0:
                    pct = (nulls / total) * 100
                    issues.append({
                        'tabla': table,
                        'columna': col,
                        'nulos': nulls,
                        'pct': round(pct, 2)
                    })
    # Output JSON
    print(json.dumps(issues, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    audit_gold_nulls()
