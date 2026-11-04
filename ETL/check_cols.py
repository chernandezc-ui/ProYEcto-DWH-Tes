import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config.conexion import obtener_engine
from sqlalchemy import text

def check_cols():
    engine = obtener_engine()
    with engine.connect() as conn:
        cols = conn.execute(text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'Bronce' AND TABLE_NAME = 'Tasa_Crecimiento_Brotes'
        """)).fetchall()
        print("Columns in Bronce.Tasa_Crecimiento_Brotes:")
        for c in cols:
            print(c[0])

if __name__ == '__main__':
    check_cols()
