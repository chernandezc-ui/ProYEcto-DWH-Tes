import sys
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\backend")
from nucleo.conexion import obtener_engine

def auditar_campanas():
    engine = obtener_engine()
    
    tablas_fact = [
        'Silver.Fact_Fisiologia',
        'Silver.Fact_Telemetria_Clima',
        'Silver.Fact_Evaluacion_Pesos',
        'Silver.Fact_Induccion_Floral',
        'Silver.Fact_Tasa_Crecimiento_Brotes',
        'Silver.Fact_Cosecha'
    ]
    
    print("=== REPORTE DE INTEGRIDAD DE CAMPAÑAS ===")
    print(f"{'Tabla':<40} | {'Total':>10} | {'Sin Campaña':>12} | {'% Error':>8}")
    print("-" * 80)
    
    for tabla in tablas_fact:
        try:
            with engine.connect() as conn:
                # Verificar si la columna existe antes
                check_col = conn.execute(text(f"SELECT COUNT(*) FROM sys.columns WHERE object_id = OBJECT_ID('{tabla}') AND name = 'ID_Campana'")).scalar()
                if not check_col:
                    print(f"{tabla:<40} | NO TIENE COLUMNA ID_Campana")
                    continue

                sql = f"""
                    SELECT 
                        COUNT(*) as Total,
                        SUM(CASE WHEN ID_Campana IS NULL OR ID_Campana <= 0 THEN 1 ELSE 0 END) as Sin_Campana
                    FROM {tabla}
                """
                res = conn.execute(text(sql)).fetchone()
                total = res.Total or 0
                sin_camp = res.Sin_Campana or 0
                pct = (sin_camp / total * 100) if total > 0 else 0
                
                print(f"{tabla:<40} | {total:>10,} | {sin_camp:>12,} | {pct:>7.1f}%")
                
                if sin_camp > 0:
                    # Ver detalle de fechas de los huérfanos
                    sql_det = f"""
                        SELECT TOP 5 
                            YEAR(Fecha_Evento) as Anio, 
                            MONTH(Fecha_Evento) as Mes, 
                            COUNT(*) as Cantidad
                        FROM {tabla}
                        WHERE ID_Campana IS NULL OR ID_Campana <= 0
                        GROUP BY YEAR(Fecha_Evento), MONTH(Fecha_Evento)
                        ORDER BY Anio DESC, Mes DESC
                    """
                    detalles = conn.execute(text(sql_det)).fetchall()
                    if detalles:
                        print(f"   -> Muestra de huérfanos: {', '.join([f'{d.Anio}-{d.Mes:02d} ({d.Cantidad})' for d in detalles])}")
        
        except Exception as e:
            print(f"{tabla:<40} | ERROR: {str(e)[:50]}")

    print("-" * 80)
    print("Nota: ID_Campana <= 0 incluye NULLs y el ID -1 (Desconocido).")

if __name__ == "__main__":
    auditar_campanas()
