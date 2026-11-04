import sys
import os
from pathlib import Path
from sqlalchemy import text

_DIR_PROYECTO = Path(__file__).resolve().parents[2]
if str(_DIR_PROYECTO) not in sys.path:
    sys.path.insert(0, str(_DIR_PROYECTO))

from comun.conexion import obtener_engine

def count_rows():
    engine = obtener_engine()
    with engine.connect() as conn:
        res = conn.execute(text("SELECT COUNT(*) FROM Bronce.Evaluacion_Vegetativa")).scalar()
        print(f"Filas en Bronce.Evaluacion_Vegetativa: {res}")

if __name__ == "__main__":
    count_rows()
