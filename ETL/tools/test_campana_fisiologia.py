import sys
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL")
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\backend")
from silver.facts.fact_fisiologia import cargar_fact_fisiologia
from nucleo.conexion import obtener_engine
import logging

logging.basicConfig(level=logging.INFO)
engine = obtener_engine()
resumen = cargar_fact_fisiologia(engine)
print("\n--- RESUMEN FINAL ---")
print(resumen)

if resumen.get('cuarentena'):
    print("\n--- MUESTRA CUARENTENA ---")
    for item in resumen['cuarentena'][:5]:
        print(item)
