import sys
import pandas as pd
from pathlib import Path
from sqlalchemy import text

_DIR_PROYECTO = Path(__file__).resolve().parents[2]
if str(_DIR_PROYECTO) not in sys.path:
    sys.path.insert(0, str(_DIR_PROYECTO))

from comun.conexion import obtener_engine

def verificar_flujo():
    engine = obtener_engine()
    
    # Mapeo de tablas de flujo
    flujos = [
        ("Cosecha", "Bronce.Cosecha_SAP", "Silver.Fact_Cosecha_SAP", "Gold.Mart_Cosecha"),
        ("Conteo Fenologico", "Bronce.Conteo_Fenologico", "Silver.Fact_Conteo_Fenologico", "Gold.Mart_Fenologia"),
        ("Ciclos Fenologicos", "Bronce.Ciclos_Fenologicos", "Silver.Fact_Ciclos_Fenologicos", "Gold.Mart_Fenologia"),
        ("Peladas", "Bronce.Peladas", "Silver.Fact_Peladas", "Gold.Mart_Fenologia"),
        ("Clima", "Bronce.Telemetria_Clima", "Silver.Fact_Telemetria_Clima", "Gold.Mart_Clima"),
        ("Pesos", "Bronce.Evaluacion_Pesos", "Silver.Fact_Evaluacion_Pesos", "Gold.Mart_Pesos_Calibres"),
        ("Fisiologia", "Bronce.Fisiologia", "Silver.Fact_Fisiologia", "Gold.Mart_Fisiologia"),
        ("Floracion", "Bronce.Floracion", "Silver.Fact_Floracion", "Gold.Mart_Fenologia"),
        ("Induccion", "Bronce.Induccion_Floral", "Silver.Fact_Induccion_Floral", "Gold.Mart_Induccion_Floral"),
        ("Tasa Crecimiento", "Bronce.Tasa_Crecimiento_Brotes", "Silver.Fact_Tasa_Crecimiento_Brotes", "Gold.Mart_Tasa_Crecimiento"),
        ("Censo Plantas", "Bronce.Censo_Plantas", "Silver.Fact_Censo_Plantas", "Gold.Mart_Censo_Plantas"),
        ("Evaluacion Vegetativa", "Bronce.Evaluacion_Vegetativa", "Silver.Fact_Evaluacion_Vegetativa", "Gold.Mart_Evaluacion_Vegetativa"),
        ("Areas Plantas", "Bronce.Areas_Plantas", "Silver.Fact_Areas_Plantas", "Gold.Mart_Administrativo")
    ]
    
    resultados = []
    
    with engine.connect() as conn:
        for nombre, bronce, silver, gold in flujos:
            try:
                # Contar Bronce
                c_bronce = conn.execute(text(f"SELECT COUNT(*) FROM {bronce}")).scalar()
            except Exception:
                c_bronce = 0
                
            try:
                # Contar Silver
                c_silver = conn.execute(text(f"SELECT COUNT(*) FROM {silver}")).scalar()
            except Exception:
                c_silver = 0
                
            try:
                # Contar Gold
                c_gold = conn.execute(text(f"SELECT COUNT(*) FROM {gold}")).scalar()
            except Exception:
                c_gold = 0
                
            resultados.append({
                "Dominio": nombre,
                "Bronce": c_bronce,
                "Silver": c_silver,
                "Gold": c_gold
            })
            
    df = pd.DataFrame(resultados)
    print("\n================== REPORTE DE FLUJO DE DATOS ==================")
    print(df.to_string(index=False))
    print("===============================================================\n")

if __name__ == "__main__":
    verificar_flujo()
