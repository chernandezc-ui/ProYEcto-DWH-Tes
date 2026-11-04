"""
audit_ev.py
===========
Diagnóstico completo del pipeline de Evaluacion Vegetativa:
Script -> Bronce -> Silver -> Gold
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.conexion import obtener_engine
from sqlalchemy import text

engine = obtener_engine()

with engine.connect() as conn:
    # 1. Columnas físicas de Bronce
    filas = conn.execute(text("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'Bronce'
          AND TABLE_NAME = 'Evaluacion_Vegetativa'
        ORDER BY ORDINAL_POSITION
    """)).fetchall()
    print("=== Bronce.Evaluacion_Vegetativa (columnas) ===")
    for f in filas:
        print(f"  {f[0]:45s} {f[1]:20s} {f[2]}")

    # 2. Conteo total y por estado
    print("\n=== Conteos Bronce ===")
    cnt = conn.execute(text("SELECT COUNT(*) FROM Bronce.Evaluacion_Vegetativa")).scalar()
    print(f"  Total filas: {cnt}")

    estados = conn.execute(text("""
        SELECT Estado_Carga, COUNT(*) as n
        FROM Bronce.Evaluacion_Vegetativa
        GROUP BY Estado_Carga
    """)).fetchall()
    for e in estados:
        print(f"  Estado={e[0]}: {e[1]}")

    # 3. Muestra de datos Bronce (filas CARGADO)
    print("\n=== Muestra Bronce (primeras 3 CARGADO) ===")
    muestra = conn.execute(text("""
        SELECT TOP 3
            ID_Evaluacion_Veg,
            Fecha_Raw, Modulo_Raw, Variedad_Raw,
            Altura_Raw, Tallos_Basales_Raw, Tallos_Basales_Nuevos_Raw,
            Piso1_Brotes_Raw, Piso1_Productivos_Raw, Piso1_Diametro_Raw,
            Piso2_Brotes_Raw, Piso3_Brotes_Raw,
            Valores_Raw
        FROM Bronce.Evaluacion_Vegetativa
        WHERE Estado_Carga = 'CARGADO'
    """)).fetchall()
    for row in muestra:
        print(f"  ID={row[0]} | Fecha={row[1]} | Modulo={row[2]} | Var={row[3]}")
        print(f"  Altura={row[4]} | TB={row[5]} | TBN={row[6]}")
        print(f"  P1B={row[7]} | P1P={row[8]} | P1D={row[9]}")
        print(f"  P2B={row[10]} | P3B={row[11]}")
        print(f"  ValoresRaw={str(row[12])[:300]}")
        print()

    # 4. ¿Cuántos tienen Piso1_Brotes_Raw nulo vs con datos?
    print("=== Análisis Nulos en Piso*_Raw ===")
    nulos = conn.execute(text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN Piso1_Brotes_Raw IS NULL THEN 1 ELSE 0 END) as P1B_nulo,
            SUM(CASE WHEN Piso1_Productivos_Raw IS NULL THEN 1 ELSE 0 END) as P1P_nulo,
            SUM(CASE WHEN Piso1_Diametro_Raw IS NULL THEN 1 ELSE 0 END) as P1D_nulo,
            SUM(CASE WHEN Valores_Raw IS NULL THEN 1 ELSE 0 END) as ValRaw_nulo
        FROM Bronce.Evaluacion_Vegetativa
        WHERE Estado_Carga = 'CARGADO'
    """)).fetchone()
    print(f"  Total CARGADO: {nulos[0]}")
    print(f"  Piso1_Brotes_Raw nulo: {nulos[1]}")
    print(f"  Piso1_Productivos_Raw nulo: {nulos[2]}")
    print(f"  Piso1_Diametro_Raw nulo: {nulos[3]}")
    print(f"  Valores_Raw nulo: {nulos[4]}")

    # 5. Silver - conteo
    print("\n=== Silver.Fact_Evaluacion_Vegetativa ===")
    try:
        s_cnt = conn.execute(text("SELECT COUNT(*) FROM Silver.Fact_Evaluacion_Vegetativa")).scalar()
        print(f"  Total filas Silver: {s_cnt}")
        s_muestra = conn.execute(text("""
            SELECT TOP 3
                ID_Evaluacion_Veg,
                ID_Geografia, ID_Tiempo, ID_Variedad, ID_Campana,
                Piso, Brotes_Generales, Brotes_Productivos, Diametro_Brote,
                Altura, Tallos_Basales, Estado_DQ
            FROM Silver.Fact_Evaluacion_Vegetativa
        """)).fetchall()
        for row in s_muestra:
            print(f"  ID={row[0]} | Geo={row[1]} | T={row[2]} | V={row[3]} | C={row[4]}")
            print(f"  Piso={row[5]} | BG={row[6]} | BP={row[7]} | D={row[8]}")
            print(f"  Altura={row[9]} | TB={row[10]} | DQ={row[11]}")
            print()
    except Exception as e:
        print(f"  ERROR leyendo Silver: {e}")

    # 6. Gold
    print("=== Gold (evaluacion vegetativa) ===")
    try:
        # Buscar tabla Gold relacionada
        g_tbls = conn.execute(text("""
            SELECT TABLE_SCHEMA, TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME LIKE '%Evaluacion%'
               OR TABLE_NAME LIKE '%Vegetativa%'
        """)).fetchall()
        for t in g_tbls:
            print(f"  Tabla: {t[0]}.{t[1]}")
            c2 = conn.execute(text(f"SELECT COUNT(*) FROM [{t[0]}].[{t[1]}]")).scalar()
            print(f"    Filas: {c2}")
    except Exception as e:
        print(f"  ERROR buscando Gold: {e}")

print("\nDiagnóstico completo.")
