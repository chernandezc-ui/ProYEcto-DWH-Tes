import sys
import os
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.conexion import obtener_engine
from gold.marts import refrescar_todos_los_marts

def refresh_gold():
    engine = obtener_engine()
    # Empty resumen_etl and no facts blockades (refresh all)
    resumen = {}
    try:
        result = refrescar_todos_los_marts(engine, resumen_etl=resumen, facts_bloqueantes=frozenset())
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error al refrescar Gold: {e}")

if __name__ == '__main__':
    refresh_gold()
