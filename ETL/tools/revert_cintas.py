import sys
from pathlib import Path
from sqlalchemy import text

_DIR_PROYECTO = Path(__file__).resolve().parents[2]
if str(_DIR_PROYECTO) not in sys.path:
    sys.path.insert(0, str(_DIR_PROYECTO))

from comun.conexion import obtener_engine

def revert_cintas():
    engine = obtener_engine()
    with engine.begin() as conn:
        # First, delete from Fact_Ciclos_Fenologicos to avoid FK constraint errors if any
        # Or better yet, we just delete the cintas. Since the pipeline will truncate or overwrite the fact table anyway.
        # But wait, Fact_Ciclos_Fenologicos has these IDs right now.
        print("Borrando registros duplicados de Fact_Ciclos_Fenologicos...")
        conn.execute(text("DELETE FROM Silver.Fact_Ciclos_Fenologicos WHERE ID_Cinta IN (16, 17, 18)"))
        
        print("Borrando cintas duplicadas de Silver.Dim_Cinta...")
        res = conn.execute(text("DELETE FROM Silver.Dim_Cinta WHERE ID_Cinta IN (16, 17, 18)"))
        print(f"Borrados {res.rowcount} registros de Dim_Cinta.")

if __name__ == "__main__":
    revert_cintas()
