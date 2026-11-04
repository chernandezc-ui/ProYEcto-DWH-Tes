"""
audit_ev3.py - Diagnóstico profundo de qué hay en Silver y Gold
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.conexion import obtener_engine
from sqlalchemy import text

engine = obtener_engine()
with engine.connect() as conn:
    # 1. ¿Cuántos registros Silver tienen pisos con datos > 0?
    print("=== Análisis de ceros en Silver ===")
    r = conn.execute(text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN Brotes_Generales > 0 THEN 1 ELSE 0 END) as tiene_BG,
            SUM(CASE WHEN Brotes_Productivos > 0 THEN 1 ELSE 0 END) as tiene_BP,
            SUM(CASE WHEN Diametro_Brote > 0 THEN 1 ELSE 0 END) as tiene_D,
            SUM(CASE WHEN Altura > 0 THEN 1 ELSE 0 END) as tiene_Altura,
            SUM(CASE WHEN Tallos_Basales > 0 THEN 1 ELSE 0 END) as tiene_TB
        FROM Silver.Fact_Evaluacion_Vegetativa
    """)).fetchone()
    print(f"  Total Silver: {r[0]}")
    print(f"  Con BG > 0:   {r[1]}")
    print(f"  Con BP > 0:   {r[2]}")
    print(f"  Con D > 0:    {r[3]}")
    print(f"  Con Altura>0: {r[4]}")
    print(f"  Con TB > 0:   {r[5]}")

    # 2. Bronce: ¿hay datos con pisos cargados?
    print("\n=== Bronce: Estado de los pisos ===")
    r2 = conn.execute(text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN Piso1_Brotes_Raw IS NOT NULL AND Piso1_Brotes_Raw <> '' THEN 1 ELSE 0 END) as P1B_ok,
            SUM(CASE WHEN Piso2_Brotes_Raw IS NOT NULL AND Piso2_Brotes_Raw <> '' THEN 1 ELSE 0 END) as P2B_ok,
            SUM(CASE WHEN Piso3_Brotes_Raw IS NOT NULL AND Piso3_Brotes_Raw <> '' THEN 1 ELSE 0 END) as P3B_ok,
            SUM(CASE WHEN Altura_Raw IS NOT NULL AND Altura_Raw <> '' THEN 1 ELSE 0 END) as Alt_ok,
            SUM(CASE WHEN Tallos_Basales_Raw IS NOT NULL AND Tallos_Basales_Raw <> '' THEN 1 ELSE 0 END) as TB_ok,
            SUM(CASE WHEN Valores_Raw IS NOT NULL AND Valores_Raw <> '' THEN 1 ELSE 0 END) as ValRaw_ok
        FROM Bronce.Evaluacion_Vegetativa
    """)).fetchone()
    print(f"  Total Bronce: {r2[0]}")
    print(f"  Piso1_Brotes con dato: {r2[1]}")
    print(f"  Piso2_Brotes con dato: {r2[2]}")
    print(f"  Piso3_Brotes con dato: {r2[3]}")
    print(f"  Altura con dato:       {r2[4]}")
    print(f"  Tallos_Basales dato:   {r2[5]}")
    print(f"  Valores_Raw con dato:  {r2[6]}")

    # 3. Muestra de Bronce con pisos reales
    print("\n=== Muestra Bronce con pisos ===")
    m = conn.execute(text("""
        SELECT TOP 5
            ID_Evaluacion_Veg, Estado_Carga,
            Fecha_Raw, Modulo_Raw, Variedad_Raw,
            Altura_Raw, Tallos_Basales_Raw,
            Piso1_Brotes_Raw, Piso1_Productivos_Raw, Piso1_Diametro_Raw,
            Piso2_Brotes_Raw, Piso3_Brotes_Raw, Piso4_Brotes_Raw, Piso5_Brotes_Raw,
            Valores_Raw
        FROM Bronce.Evaluacion_Vegetativa
        WHERE Piso1_Brotes_Raw IS NOT NULL AND Piso1_Brotes_Raw <> ''
    """)).fetchall()
    if m:
        for r in m:
            print(f"  ID={r[0]} Estado={r[1]}")
            print(f"  P1B={r[7]} P2B={r[10]} P3B={r[11]} P4B={r[12]} P5B={r[13]}")
    else:
        print("  NO HAY filas con Piso1_Brotes_Raw con valor!")
        # Mirar Valores_Raw para ver si están ahí los datos
        m2 = conn.execute(text("""
            SELECT TOP 3
                ID_Evaluacion_Veg, Estado_Carga,
                Fecha_Raw, Modulo_Raw, Variedad_Raw,
                Altura_Raw, Tallos_Basales_Raw, Valores_Raw
            FROM Bronce.Evaluacion_Vegetativa
            WHERE Valores_Raw IS NOT NULL AND Valores_Raw <> ''
        """)).fetchall()
        print("  Muestra con Valores_Raw:")
        for r in m2:
            print(f"    ID={r[0]} Estado={r[1]}")
            print(f"    Altura={r[5]} TB={r[6]}")
            print(f"    Valores_Raw={str(r[7])[:500]}")
            print()

    # 4. Gold: columnas de Mart_Evaluacion_Vegetativa
    print("\n=== Gold.Mart_Evaluacion_Vegetativa (columnas) ===")
    gcols = conn.execute(text("""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'Gold'
          AND TABLE_NAME = 'Mart_Evaluacion_Vegetativa'
        ORDER BY ORDINAL_POSITION
    """)).fetchall()
    for c in gcols:
        print(f"  {c[0]:40s} {c[1]}")

    # Muestra Gold
    print("\n=== Muestra Gold (3 filas) ===")
    gm = conn.execute(text("SELECT TOP 3 * FROM Gold.Mart_Evaluacion_Vegetativa")).fetchall()
    if gm:
        for r in gm:
            print(f"  {r}")

print("\nAudit3 completado.")
