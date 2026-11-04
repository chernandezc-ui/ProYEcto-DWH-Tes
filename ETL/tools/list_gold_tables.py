import sys
import os
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.conexion import obtener_engine
from sqlalchemy import text

def list_gold_tables():
    engine = obtener_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT TABLE_SCHEMA, TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'Gold'
        """)).fetchall()
        tables = [f"{schema}.{name}" for schema, name in rows]
        print(json.dumps(tables, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    list_gold_tables()
