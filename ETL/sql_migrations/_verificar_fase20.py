"""Verifica las 13 vistas PowerBI.vw_* de la fase 20.

Reglas:
1. Las 13 vistas existen y son consultables.
2. Para Marts no vacíos, COUNT(vista) == COUNT(mart).
3. Ninguna vista expone columnas ID_* de lookup; solo se permite ID_Mart_*.
"""
import sys
import pyodbc

CN = (
    "DRIVER={ODBC Driver 17 for SQL Server};SERVER=.;"
    "DATABASE=ACP_DataWarehose_Proyecciones;Trusted_Connection=yes"
)

PARES = {
    "vw_Cosecha": "Mart_Cosecha",
    "vw_Censo_Plantas": "Mart_Censo_Plantas",
    "vw_Ciclo_Poda": "Mart_Ciclo_Poda",
    "vw_Evaluacion_Vegetativa": "Mart_Evaluacion_Vegetativa",
    "vw_Fisiologia": "Mart_Fisiologia",
    "vw_Induccion_Floral": "Mart_Induccion_Floral",
    "vw_Tasa_Crecimiento": "Mart_Tasa_Crecimiento",
    "vw_Pesos_Calibres": "Mart_Pesos_Calibres",
    "vw_Proyecciones": "Mart_Proyecciones",
    "vw_Maduracion": "Mart_Maduracion",
    "vw_Clima": "Mart_Clima",
    "vw_Administrativo": "Mart_Administrativo",
    "vw_Fenologia": "Mart_Fenologia",
}

def main() -> int:
    cn = pyodbc.connect(CN)
    cur = cn.cursor()
    fallos = []

    for vista, mart in PARES.items():
        try:
            n_vista = cur.execute(f"SELECT COUNT(*) FROM PowerBI.{vista}").fetchval()
        except pyodbc.Error as e:
            fallos.append(f"[{vista}] no consultable: {e}")
            continue
        n_mart = cur.execute(f"SELECT COUNT(*) FROM Gold.{mart}").fetchval()
        if n_mart > 0 and n_vista != n_mart:
            fallos.append(f"[{vista}] conteo {n_vista} != mart {n_mart}")

        cols = [r.COLUMN_NAME for r in cur.execute(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA='PowerBI' AND TABLE_NAME=?", vista
        ).fetchall()]
        malas = [c for c in cols
                 if c.upper().startswith("ID_") and not c.upper().startswith("ID_MART")]
        if malas:
            fallos.append(f"[{vista}] expone IDs de lookup: {malas}")

    total = cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_SCHEMA='PowerBI'"
    ).fetchval()
    if total != 13:
        fallos.append(f"Se esperaban 13 vistas en PowerBI, hay {total}")

    if fallos:
        print("VERIFICACION FALLIDA:")
        for f in fallos:
            print("  -", f)
        return 1
    print(f"OK: {total} vistas PowerBI.vw_* validadas (conteos e IDs correctos).")
    return 0

if __name__ == "__main__":
    sys.exit(main())
