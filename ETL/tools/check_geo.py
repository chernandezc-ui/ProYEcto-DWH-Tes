import sys
import os
from pathlib import Path
from sqlalchemy import text

_DIR_PROYECTO = Path(__file__).resolve().parents[2]
if str(_DIR_PROYECTO) not in sys.path:
    sys.path.insert(0, str(_DIR_PROYECTO))

from comun.conexion import obtener_engine

def check_geo():
    engine = obtener_engine()
    with engine.connect() as conn:
        res = conn.execute(text("SELECT COUNT(*) FROM MDM.Catalogo_Geografia")).scalar()
        print(f"Filas en MDM.Catalogo_Geografia: {res}")
        res_dim = conn.execute(text("SELECT COUNT(*) FROM Silver.Dim_Geografia")).scalar()
        print(f"Filas en Silver.Dim_Geografia: {res_dim}")

if __name__ == "__main__":
    check_geo()
