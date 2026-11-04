import pandas as pd
from sqlalchemy import create_engine, text

def inventario_completo():
    conn_str = "mssql+pyodbc://LCP-PAG-PRACTIC/ACP_DataWarehose_Proyecciones?driver=ODBC+Driver+17+for+SQL+Server&Trusted_Connection=yes"
    engine = create_engine(conn_str)
    
    with engine.connect() as conn:
        print("==================================================================")
        print("          INVENTARIO GLOBAL: ACP DATAWAREHOUSE PROJECT")
        print("==================================================================\n")
        
        # 1. Obtener lista de tablas, esquemas y conteo de columnas
        sql_tablas = text("""
            SELECT 
                t.TABLE_SCHEMA, 
                t.TABLE_NAME,
                COUNT(c.COLUMN_NAME) as Num_Columnas
            FROM INFORMATION_SCHEMA.TABLES t
            JOIN INFORMATION_SCHEMA.COLUMNS c 
                ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
            WHERE t.TABLE_TYPE = 'BASE TABLE'
              AND t.TABLE_SCHEMA IN ('Silver', 'Bronce', 'Gold', 'MDM')
            GROUP BY t.TABLE_SCHEMA, t.TABLE_NAME
            ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME
        """)
        
        tablas = conn.execute(sql_tablas).fetchall()
        
        resumen = []
        for esquema, nombre, num_cols in tablas:
            # 2. Obtener conteo de filas rápido vía sys.partitions
            sql_rows = text(f"""
                SELECT SUM(rows) 
                FROM sys.partitions 
                WHERE object_id = OBJECT_ID('{esquema}.{nombre}') 
                  AND index_id IN (0, 1)
            """)
            num_filas = conn.execute(sql_rows).scalar() or 0
            
            resumen.append({
                'Esquema': esquema,
                'Tabla': nombre,
                'Columnas': num_cols,
                'Filas': num_filas
            })

        df = pd.DataFrame(resumen)
        
        # Mostrar por esquema
        for esquema in df['Esquema'].unique():
            print(f"ESQUEMA: {esquema}")
            subset = df[df['Esquema'] == esquema]
            for _, row in subset.iterrows():
                print(f"   - {row['Tabla']:35} | Cols: {row['Columnas']:2} | Filas: {row['Filas']:,}")
            print("-" * 66)

        print(f"\nTotal de tablas encontradas: {len(df)}")

if __name__ == '__main__':
    inventario_completo()
