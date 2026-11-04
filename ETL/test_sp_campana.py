import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config.conexion import obtener_engine
from sqlalchemy import text

def test_sp():
    engine = obtener_engine()
    try:
        with engine.begin() as conn:
            conn.execute(text("EXEC Silver.sp_Sincronizar_Periodos_Campana"))
        print("Success")
    except Exception as e:
        print("Error executing SP:")
        print(e)
        
    try:
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM Silver.Bridge_Modulo_Campana")).scalar()
            print(f"Count of Bridge_Modulo_Campana: {count}")
    except Exception as e:
        print("Error getting count:")
        print(e)

if __name__ == '__main__':
    test_sp()
