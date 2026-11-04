import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config.conexion import obtener_engine
from sqlalchemy import text
import pandas as pd

def check_tables():
    engine = obtener_engine()
    with engine.connect() as conn:
        print("--- Silver Tables ---")
        tables = conn.execute(text("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME LIKE 'Bridge_%'
        """)).fetchall()
        for t in tables:
            name = t[0]
            count = conn.execute(text(f"SELECT COUNT(*) FROM Silver.{name}")).scalar()
            print(f"{name}: {count} rows")
            
        print("--- Gold Tables ---")
        tables_gold = conn.execute(text("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'Gold' 
        """)).fetchall()
        for t in tables_gold:
            name = t[0]
            count = conn.execute(text(f"SELECT COUNT(*) FROM Gold.{name}")).scalar()
            print(f"{name}: {count} rows")

if __name__ == '__main__':
    check_tables()
