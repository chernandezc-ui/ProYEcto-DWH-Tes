import pandas as pd
from sqlalchemy import create_engine, text
import re

def auditar_columnas_conteo():
    conn_str = "mssql+pyodbc://LCP-PAG-PRACTIC/ACP_DataWarehose_Proyecciones?driver=ODBC+Driver+17+for+SQL+Server&Trusted_Connection=yes"
    engine = create_engine(conn_str)
    
    with engine.connect() as conn:
        print("=== AUDITORÍA DE COLUMNAS: CONTEO FENOLÓGICO ===\n")
        
        # 1. Columnas en Silver
        res_silver = conn.execute(text("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME = 'Fact_Conteo_Fenologico'"))
        cols_silver = {row[0].lower() for row in res_silver}
        
        # 2. Datos de muestra en Bronze para analizar 'Valores_Raw'
        res_bronze = conn.execute(text("SELECT TOP 1 Valores_Raw FROM Bronce.Conteo_Fruta WHERE Valores_Raw IS NOT NULL"))
        sample = res_bronze.fetchone()
        
        campos_en_bronce_virtuales = []
        if sample:
            # Parseamos las claves del campo Valores_Raw (ej: Key1=Val1 | Key2=Val2)
            crudo = sample[0]
            for parte in re.split(r"\s*\|\s*", crudo):
                if "=" in parte:
                    clave = parte.split("=", 1)[0].replace("_Raw", "").strip()
                    campos_en_bronce_virtuales.append(clave)

        print("--- COLUMNAS DISPONIBLES EN BRONCE (DENTRO DE VALORES_RAW) ---")
        for campo in campos_en_bronce_virtuales:
            estado = "✅ MAPEO EXISTENTE" if campo.lower() in cols_silver or (campo.lower() == 'punto') else "❌ FALTA EN SILVER"
            print(f" - {campo:25} -> {estado}")
            
        print("\n--- COLUMNAS ACTUALES EN SILVER ---")
        for col in sorted(list(cols_silver)):
            print(f" - {col}")

        print("\n📝 NOTA: Para incluir las columnas marcadas con '❌', debemos ejecutar un ALTER TABLE en Silver.")

if __name__ == '__main__':
    auditar_columnas_conteo()
