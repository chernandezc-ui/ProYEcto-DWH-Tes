import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config.conexion import obtener_engine
from sqlalchemy import text

def main():
    """Herramienta manual: un error SQL debe terminar con código distinto de cero."""
    engine = obtener_engine()
    with engine.begin() as conn:
        conn.execute(text("EXEC Silver.sp_Sincronizar_Periodos_Campana"))
    print("Success")
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM Silver.Bridge_Modulo_Campana")).scalar()
        print(f"Count of Bridge_Modulo_Campana: {count}")

if __name__ == '__main__':
    main()
