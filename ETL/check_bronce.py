import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config.conexion import obtener_engine
from sqlalchemy import text

def check_bronce():
    engine = obtener_engine()
    with engine.connect() as conn:
        print("--- Bronce Tables ---")
        tables = conn.execute(text("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'Bronce' 
        """)).fetchall()
        for t in tables:
            name = t[0]
            count = conn.execute(text(f"SELECT COUNT(*) FROM Bronce.{name}")).scalar()
            print(f"{name}: {count} rows")

if __name__ == '__main__':
    check_bronce()
