"""
auditoria_flujo_bronce_silver_gold.py
=====================================
Auditoría one-shot del flujo Bronce -> Silver -> Gold para las tablas
prioritarias que no llegan / llegan al 1%. NO modifica datos: solo lee.

Salida: reporte por tabla con
  - conteo Bronce total + distribución de Estado_Carga
  - conteo Silver destino
  - conteo Gold mart (si aplica)
  - top motivos de Cuarentena ligados a la tabla
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.conexion import obtener_engine
from sqlalchemy import text

# (etiqueta, tabla_bronce, columna_id, tabla_silver, mart_gold|None)
MAPA = [
    ('Censo_Plantas',        'Bronce.Censo_Plantas',       'ID_Censo_Plantas',   'Silver.Fact_Censo_Plantas',         None),
    ('Ciclos_Fenologicos',   'Bronce.Ciclos_Fenologicos',  None,                 'Silver.Fact_Ciclos_Fenologicos',    None),
    ('Evaluacion_Vegetativa','Bronce.Evaluacion_Vegetativa',None,                'Silver.Fact_Evaluacion_Vegetativa', 'Gold.Mart_Evaluacion_Vegetativa'),
    ('Data_SAP',             'Bronce.Data_SAP',            None,                 'Silver.Fact_Cosecha_SAP',           'Gold.Mart_Cosecha'),
    ('Evaluacion_Pesos',     'Bronce.Evaluacion_Pesos',    None,                 'Silver.Fact_Evaluacion_Pesos',      'Gold.Mart_Pesos_Calibres'),
    ('Induccion_Floral',     'Bronce.Induccion_Floral',    None,                 'Silver.Fact_Induccion_Floral',      'Gold.Mart_Induccion_Floral'),
    ('Floracion',            'Bronce.Floracion',           None,                 'Silver.Fact_Floracion',             None),
    ('Peladas(veg_pesos?)',  'Bronce.Peladas',             None,                 'Silver.Fact_Peladas',               'Gold.Mart_Peladas'),
    ('Ciclo_Poda',           'Bronce.Evaluacion_Calidad_Poda', None,             'Silver.Fact_Ciclo_Poda',            'Gold.Mart_Ciclo_Poda'),
]


def _existe_tabla(conn, full_name: str) -> bool:
    esquema, tabla = full_name.split('.', 1)
    r = conn.execute(text("""
        SELECT 1 FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
        WHERE s.name=:e AND t.name=:t
    """), {'e': esquema, 't': tabla}).fetchone()
    return r is not None


def _cols(conn, full_name: str) -> set[str]:
    esquema, tabla = full_name.split('.', 1)
    rows = conn.execute(text("""
        SELECT c.name FROM sys.columns c
        JOIN sys.tables t ON t.object_id=c.object_id
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        WHERE s.name=:e AND t.name=:t
    """), {'e': esquema, 't': tabla}).fetchall()
    return {r[0] for r in rows}


def _count(conn, full_name: str) -> int:
    return int(conn.execute(text(f"SELECT COUNT(*) FROM {full_name}")).scalar() or 0)


def _dist_estado(conn, full_name: str, cols: set[str]) -> dict:
    if 'Estado_Carga' not in cols:
        return {'(sin columna Estado_Carga)': _count(conn, full_name)}
    rows = conn.execute(text(f"""
        SELECT ISNULL(Estado_Carga,'(NULL)') AS e, COUNT(*) c
        FROM {full_name} GROUP BY Estado_Carga ORDER BY c DESC
    """)).fetchall()
    return {r[0]: int(r[1]) for r in rows}


def _cuarentena_tablas(conn) -> list[str]:
    rows = conn.execute(text("""
        SELECT s.name+'.'+t.name
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
        WHERE s.name='Cuarentena'
    """)).fetchall()
    return [r[0] for r in rows]


def main():
    engine = obtener_engine()
    with engine.connect() as conn:
        print("=" * 78)
        print("AUDITORÍA FLUJO BRONCE -> SILVER -> GOLD")
        print("=" * 78)

        # Inventario de cuarentena disponible
        cuar_tabs = _cuarentena_tablas(conn)
        print(f"\nTablas en esquema Cuarentena: {cuar_tabs}\n")

        for etiqueta, t_bronce, col_id, t_silver, mart in MAPA:
            print("-" * 78)
            print(f"[{etiqueta}]")
            if not _existe_tabla(conn, t_bronce):
                print(f"  Bronce {t_bronce}: NO EXISTE")
                continue
            cols_b = _cols(conn, t_bronce)
            total_b = _count(conn, t_bronce)
            dist = _dist_estado(conn, t_bronce, cols_b)
            print(f"  Bronce {t_bronce}: {total_b:,} filas")
            for e, c in dist.items():
                pct = (c / total_b * 100) if total_b else 0
                print(f"      Estado_Carga={e:<14} {c:>10,}  ({pct:5.1f}%)")

            if _existe_tabla(conn, t_silver):
                total_s = _count(conn, t_silver)
                ratio = (total_s / total_b * 100) if total_b else 0
                print(f"  Silver {t_silver}: {total_s:,} filas   -> {ratio:.1f}% del Bronce")
            else:
                print(f"  Silver {t_silver}: NO EXISTE")

            if mart:
                if _existe_tabla(conn, mart):
                    print(f"  Gold   {mart}: {_count(conn, mart):,} filas")
                else:
                    print(f"  Gold   {mart}: NO EXISTE")

        print("\n" + "=" * 78)
        print("RESUMEN GLOBAL DE CUARENTENA (todos los motivos, top 40)")
        print("=" * 78)
        # Detectar la(s) tabla(s) de cuarentena con columnas motivo/tabla
        for ct in cuar_tabs:
            cc = _cols(conn, ct)
            col_motivo = next((x for x in ('Motivo', 'Motivo_Rechazo', 'Descripcion', 'Mensaje') if x in cc), None)
            col_tabla  = next((x for x in ('Tabla_Origen', 'Tabla', 'Origen', 'Tabla_Destino') if x in cc), None)
            col_col    = next((x for x in ('Columna', 'Columna_Origen', 'Campo') if x in cc), None)
            print(f"\n  >> {ct}  (motivo={col_motivo}, tabla={col_tabla}, columna={col_col})  total={_count(conn, ct):,}")
            if not col_motivo:
                print("     (sin columna de motivo reconocible; columnas:", sorted(cc), ")")
                continue
            sel_tabla = f"ISNULL(CAST({col_tabla} AS NVARCHAR(200)),'(NULL)')" if col_tabla else "'(n/a)'"
            sel_col   = f"ISNULL(CAST({col_col} AS NVARCHAR(200)),'(NULL)')" if col_col else "'(n/a)'"
            rows = conn.execute(text(f"""
                SELECT TOP 40
                    {sel_tabla} AS tabla,
                    {sel_col}   AS columna,
                    LEFT(CAST({col_motivo} AS NVARCHAR(MAX)),120) AS motivo,
                    COUNT(*) AS c
                FROM {ct}
                GROUP BY {sel_tabla}, {sel_col}, LEFT(CAST({col_motivo} AS NVARCHAR(MAX)),120)
                ORDER BY c DESC
            """)).fetchall()
            for r in rows:
                print(f"     {int(r[3]):>8,} | {r[0][:28]:<28} | {str(r[1])[:22]:<22} | {r[2]}")


if __name__ == '__main__':
    main()
