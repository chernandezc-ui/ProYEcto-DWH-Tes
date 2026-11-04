"""
backend/scripts/medir_catalogos.py
===================================
Medición one-shot para decidir Fase 2 de catálogos (council 2026-06-17).

Outputs:
  1. COUNT(*) por tabla — ¿realmente tenemos un "problema de escala"?
  2. Collation de columnas que se buscan con LIKE — ¿accent/case insensitive?
  3. Cardinalidad de los facets (breeder, rol, fundo) — ¿hardcode o endpoint?
  4. Top 5 valores de cada facet — para verificar tipos esperados.

Uso:
  .venv\\Scripts\\python.exe -m scripts.medir_catalogos > docs/decisiones/2026-06-17-catalogos-medicion.md

(Correr desde backend/ con el venv activo.)
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# Permitir ejecución desde backend/ sin instalar como paquete.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from nucleo.conexion import obtener_engine  # noqa: E402


def print_section(titulo: str) -> None:
    print(f"\n## {titulo}\n")


def ejecutar_query(con, sql: str, descripcion: str) -> None:
    print(f"### {descripcion}\n")
    print("```sql")
    print(sql.strip())
    print("```\n")
    print("**Resultado:**\n")
    try:
        filas = con.execute(text(sql)).fetchall()
        if not filas:
            print("_(sin filas)_\n")
            return
        # Imprimir como tabla Markdown.
        headers = list(filas[0]._mapping.keys())
        print("| " + " | ".join(headers) + " |")
        print("| " + " | ".join("---" for _ in headers) + " |")
        for f in filas:
            d = dict(f._mapping)
            print("| " + " | ".join(str(d[h]) if d[h] is not None else "_NULL_" for h in headers) + " |")
        print()
    except Exception as exc:  # noqa: BLE001
        print(f"**ERROR:** `{type(exc).__name__}: {exc}`\n")


def main() -> None:
    print(f"# Medición catálogos — {datetime.now().isoformat(timespec='seconds')}")
    print()
    print("Output del script `backend/scripts/medir_catalogos.py`. Sirve para")
    print("decidir si la Fase 2 (filtros server-side) está justificada o si")
    print("el portal puede seguir filtrando client-side con el TruncationWarning.")

    with obtener_engine().connect() as con:
        # ---------- 1. Tamaños ----------
        print_section("1. Tamaño real de cada catálogo")
        ejecutar_query(
            con,
            """
            SELECT 'MDM.Catalogo_Variedades' AS tabla, COUNT(*) AS filas FROM MDM.Catalogo_Variedades WITH (NOLOCK)
            UNION ALL SELECT 'Silver.Dim_Variedad',  COUNT(*) FROM Silver.Dim_Variedad WITH (NOLOCK)
            UNION ALL SELECT 'Silver.Dim_Geografia (vigente)', COUNT(*) FROM Silver.Dim_Geografia WITH (NOLOCK) WHERE Es_Vigente = 1
            UNION ALL SELECT 'Silver.Dim_Personal',  COUNT(*) FROM Silver.Dim_Personal WITH (NOLOCK)
            """,
            "Conteo por catálogo",
        )

        # ---------- 2. Collation ----------
        print_section("2. Collation de columnas de búsqueda")
        ejecutar_query(
            con,
            """
            SELECT
                c.TABLE_SCHEMA   AS esquema,
                c.TABLE_NAME     AS tabla,
                c.COLUMN_NAME    AS columna,
                c.COLLATION_NAME AS collation
            FROM INFORMATION_SCHEMA.COLUMNS c
            WHERE c.COLLATION_NAME IS NOT NULL
              AND (
                   (c.TABLE_SCHEMA = 'MDM'    AND c.TABLE_NAME = 'Catalogo_Variedades' AND c.COLUMN_NAME IN ('Nombre_Canonico','Breeder'))
                OR (c.TABLE_SCHEMA = 'Silver' AND c.TABLE_NAME = 'Dim_Variedad'         AND c.COLUMN_NAME IN ('Nombre_Variedad','Breeder'))
                OR (c.TABLE_SCHEMA = 'Silver' AND c.TABLE_NAME LIKE 'Dim_%_Catalogo'    AND c.COLUMN_NAME IN ('Fundo','Sector','Modulo','Turno','Valvula','Cama_Normalizada'))
                OR (c.TABLE_SCHEMA = 'Silver' AND c.TABLE_NAME = 'Dim_Personal'         AND c.COLUMN_NAME IN ('DNI','Nombre_Completo','Rol','ID_Planilla'))
              )
            ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.COLUMN_NAME
            """,
            "Collation por columna de búsqueda",
        )

        print(
            "_Interpretación: una collation que termina en `_CI_AI` es case-insensitive_"
            " _+ accent-insensitive — `LIKE '%garcia%'` SÍ matchea 'García'._"
            " _Si termina en `_CI_AS` o `_CS_AS`, hay que normalizar con `COLLATE` o búsquedas como 'García' fallarán._\n"
        )

        # ---------- 3. Cardinalidad facets ----------
        print_section("3. Cardinalidad de los facets")
        ejecutar_query(
            con,
            """
            SELECT
                'Silver.Dim_Variedad / Breeder'         AS facet, COUNT(DISTINCT Breeder)         AS valores_distintos FROM Silver.Dim_Variedad WITH (NOLOCK)
            UNION ALL
            SELECT
                'MDM.Catalogo_Variedades / Breeder',    COUNT(DISTINCT Breeder)                                       FROM MDM.Catalogo_Variedades WITH (NOLOCK)
            UNION ALL
            SELECT
                'Silver.Dim_Personal / Rol',            COUNT(DISTINCT Rol)                                           FROM Silver.Dim_Personal WITH (NOLOCK)
            UNION ALL
            SELECT
                'Silver.Dim_Fundo_Catalogo / Fundo',    COUNT(DISTINCT Fundo)                                         FROM Silver.Dim_Fundo_Catalogo WITH (NOLOCK)
            UNION ALL
            SELECT
                'Silver.Dim_Sector_Catalogo / Sector',  COUNT(DISTINCT Sector)                                        FROM Silver.Dim_Sector_Catalogo WITH (NOLOCK)
            """,
            "Cuántos valores distintos hay por facet",
        )

        print(
            "_Interpretación: si valores_distintos <= 20, hardcodear el dropdown_"
            " _es razonable (ahorra endpoint). Si > 50, requiere endpoint dedicado._\n"
        )

        # ---------- 4. Top valores ----------
        print_section("4. Top valores por facet (sample)")
        ejecutar_query(
            con,
            """
            SELECT TOP 10
                ISNULL(Breeder, '_(null)_') AS breeder, COUNT(*) AS variedades
            FROM Silver.Dim_Variedad WITH (NOLOCK)
            GROUP BY Breeder
            ORDER BY 2 DESC
            """,
            "Top 10 breeders (Silver.Dim_Variedad)",
        )
        ejecutar_query(
            con,
            """
            SELECT TOP 10
                ISNULL(Rol, '_(null)_') AS rol, COUNT(*) AS personas
            FROM Silver.Dim_Personal WITH (NOLOCK)
            GROUP BY Rol
            ORDER BY 2 DESC
            """,
            "Top 10 roles (Silver.Dim_Personal)",
        )

    print("\n---\n")
    print("**Próximos pasos sugeridos según resultados:**")
    print()
    print("- Si todos los catálogos están <2000 filas y collation es `_CI_AI`:")
    print("  **No migrar** — el cliente filtra perfecto. Confirmar TruncationWarning como red de seguridad.")
    print("- Si alguno supera 5000 filas o la collation es `_AS` (accent-sensitive):")
    print("  Migrar SOLO ese catálogo. Substring `LIKE '%x%'` + facets en payload.")
    print("- Si los facets de baja cardinalidad (<20): hardcodear en el cliente. Si altos: endpoint dedicado.")


if __name__ == "__main__":
    main()
