import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config.conexion import obtener_engine
from sqlalchemy import text

def check_schema():
    engine = obtener_engine()
    with engine.connect() as conn:
        res = conn.execute(text("""
            SELECT COLUMN_NAME, DATA_TYPE, NUMERIC_PRECISION, NUMERIC_SCALE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'MDM' AND TABLE_NAME = 'Diccionario_Homologacion'
            AND COLUMN_NAME = 'Score_Levenshtein'
        """)).fetchall()
        for r in res:
            print(r)

if __name__ == '__main__':
    check_schema()
