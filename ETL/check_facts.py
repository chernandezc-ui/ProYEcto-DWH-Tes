import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config.conexion import obtener_engine
from sqlalchemy import text

def check_facts():
    engine = obtener_engine()
    with engine.connect() as conn:
        print("--- Silver Fact Tables ---")
        tables = conn.execute(text("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME LIKE 'Fact_%'
        """)).fetchall()
        for t in tables:
            name = t[0]
            count = conn.execute(text(f"SELECT COUNT(*) FROM Silver.{name}")).scalar()
            print(f"{name}: {count} rows")

if __name__ == '__main__':
    check_facts()
