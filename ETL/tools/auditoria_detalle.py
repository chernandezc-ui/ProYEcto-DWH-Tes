"""Diagnóstico de detalle: motivos MDM.Cuarentena + columnas reales Bronce.
Read-only. Y ejecuta en SECO (rollback) los facts que insertan 0 para capturar
la excepción real."""
from __future__ import annotations
import sys, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.conexion import obtener_engine
from sqlalchemy import text

PRIOR_BRONCE = [
    'Bronce.Censo_Plantas', 'Bronce.Ciclos_Fenologicos', 'Bronce.Evaluacion_Vegetativa',
    'Bronce.Data_SAP', 'Bronce.Evaluacion_Pesos', 'Bronce.Induccion_Floral',
    'Bronce.Floracion', 'Bronce.Peladas', 'Bronce.Evaluacion_Calidad_Poda',
]


def cols(conn, full):
    e, t = full.split('.', 1)
    rows = conn.execute(text("""
        SELECT c.name, ty.name FROM sys.columns c
        JOIN sys.tables t ON t.object_id=c.object_id
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.types ty ON ty.user_type_id=c.user_type_id
        WHERE s.name=:e AND t.name=:t ORDER BY c.column_id
    """), {'e': e, 't': t}).fetchall()
    return [(r[0], r[1]) for r in rows]


def main():
    engine = obtener_engine()
    with engine.connect() as conn:
        # MDM.Cuarentena tablas + motivos
        print("=" * 78); print("MDM.CUARENTENA — motivos agregados"); print("=" * 78)
        cuar = conn.execute(text("""
            SELECT s.name+'.'+t.name FROM sys.tables t
            JOIN sys.schemas s ON s.schema_id=t.schema_id
            WHERE s.name='MDM' AND t.name LIKE 'Cuarentena%'
        """)).fetchall()
        for (ct,) in cuar:
            cc = [c for c, _ in cols(conn, ct)]
            total = conn.execute(text(f"SELECT COUNT(*) FROM {ct}")).scalar()
            print(f"\n>> {ct}  total={total:,}  cols={cc}")
            cmot = next((x for x in ('Motivo', 'Motivo_Rechazo', 'Detalle', 'Mensaje', 'Descripcion') if x in cc), None)
            ctab = next((x for x in ('Tabla_Origen', 'Tabla', 'Tabla_Destino', 'Origen') if x in cc), None)
            if not cmot or not total:
                continue
            seltab = ctab if ctab else "'(n/a)'"
            rows = conn.execute(text(f"""
                SELECT TOP 25 {seltab} AS tabla, LEFT(CAST({cmot} AS NVARCHAR(MAX)),100) AS m, COUNT(*) c
                FROM {ct} GROUP BY {seltab}, LEFT(CAST({cmot} AS NVARCHAR(MAX)),100) ORDER BY c DESC
            """)).fetchall()
            for r in rows:
                print(f"   {int(r[2]):>7,} | {str(r[0])[:30]:<30} | {r[1]}")

        # Columnas reales de cada Bronce prioritaria
        print("\n" + "=" * 78); print("COLUMNAS REALES BRONCE"); print("=" * 78)
        for b in PRIOR_BRONCE:
            try:
                cs = cols(conn, b)
                print(f"\n{b}:\n   " + ", ".join(f"{n}" for n, _ in cs))
            except Exception as ex:
                print(f"\n{b}: ERROR {ex}")

if __name__ == '__main__':
    main()
