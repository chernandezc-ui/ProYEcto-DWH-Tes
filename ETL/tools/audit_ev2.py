"""
audit_ev2.py - Inspección profunda de Silver y Gold para Evaluacion Vegetativa
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.conexion import obtener_engine
from sqlalchemy import text

engine = obtener_engine()
with engine.connect() as conn:
    # 1. Columnas reales de Silver.Fact_Evaluacion_Vegetativa
    cols = conn.execute(text("""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'Silver'
          AND TABLE_NAME = 'Fact_Evaluacion_Vegetativa'
        ORDER BY ORDINAL_POSITION
    """)).fetchall()
    print("=== Silver.Fact_Evaluacion_Vegetativa (columnas reales) ===")
    for c in cols:
        print(f"  {c[0]:40s} {c[1]}")

    # 2. Vista Gold
    print("\n=== Silver.vFact_Evaluacion_Vegetativa (definicion) ===")
    vdef = conn.execute(text("""
        SELECT VIEW_DEFINITION
        FROM INFORMATION_SCHEMA.VIEWS
        WHERE TABLE_SCHEMA = 'Silver'
          AND TABLE_NAME = 'vFact_Evaluacion_Vegetativa'
    """)).fetchone()
    if vdef:
        print(vdef[0][:5000])
    else:
        print("  Vista no encontrada")

    # 3. Muestra Silver con columnas correctas
    print("\n=== Muestra Silver (3 filas) ===")
    m = conn.execute(text("""
        SELECT TOP 3
            ID_Origen_Bronce, ID_Geografia, ID_Tiempo, ID_Variedad, ID_Campana,
            Piso, Brotes_Generales, Brotes_Productivos, Diametro_Brote,
            Altura, Tallos_Basales, Estado_DQ
        FROM Silver.Fact_Evaluacion_Vegetativa
    """)).fetchall()
    for r in m:
        print(f"  Orig={r[0]} Geo={r[1]} T={r[2]} V={r[3]} C={r[4]}")
        print(f"  Piso={r[5]} BG={r[6]} BP={r[7]} D={r[8]} Alt={r[9]} TB={r[10]} DQ={r[11]}")
        print()

    # 4. Tablas Gold que hay
    print("=== Tablas Gold relevantes ===")
    gold = conn.execute(text("""
        SELECT TABLE_SCHEMA, TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'Gold'
          AND (TABLE_NAME LIKE '%Vegetativa%' OR TABLE_NAME LIKE '%Evaluacion%')
    """)).fetchall()
    for t in gold:
        print(f"  {t[0]}.{t[1]}")
        try:
            cnt = conn.execute(text(f"SELECT COUNT(*) FROM [{t[0]}].[{t[1]}]")).scalar()
            print(f"    Filas: {cnt}")
        except Exception as ex:
            print(f"    ERROR: {ex}")

    # 5. Procesos que refrescan Gold
    print("\n=== Objetos que referencian vFact_Evaluacion_Vegetativa ===")
    refs = conn.execute(text("""
        SELECT OBJECT_NAME(referencing_id) as objeto,
               OBJECT_SCHEMA_NAME(referencing_id) as esquema
        FROM sys.sql_expression_dependencies
        WHERE referenced_entity_name = 'vFact_Evaluacion_Vegetativa'
    """)).fetchall()
    for r in refs:
        print(f"  {r[1]}.{r[0]}")

print("\nAudit2 completado.")
