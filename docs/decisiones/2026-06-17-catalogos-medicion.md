# Medición catálogos — 2026-06-17T12:53:10

Output del script `backend/scripts/medir_catalogos.py`. Sirve para
decidir si la Fase 2 (filtros server-side) está justificada o si
el portal puede seguir filtrando client-side con el TruncationWarning.

## 1. Tamaño real de cada catálogo

### Conteo por catálogo

```sql
SELECT 'MDM.Catalogo_Variedades' AS tabla, COUNT(*) AS filas FROM MDM.Catalogo_Variedades WITH (NOLOCK)
            UNION ALL SELECT 'Silver.Dim_Variedad',  COUNT(*) FROM Silver.Dim_Variedad WITH (NOLOCK)
            UNION ALL SELECT 'Silver.Dim_Geografia (vigente)', COUNT(*) FROM Silver.Dim_Geografia WITH (NOLOCK) WHERE Es_Vigente = 1
            UNION ALL SELECT 'Silver.Dim_Personal',  COUNT(*) FROM Silver.Dim_Personal WITH (NOLOCK)
```

**Resultado:**

| tabla | filas |
| --- | --- |
| MDM.Catalogo_Variedades | 18 |
| Silver.Dim_Variedad | 120 |
| Silver.Dim_Geografia (vigente) | 35871 |
| Silver.Dim_Personal | 232 |


## 2. Collation de columnas de búsqueda

### Collation por columna de búsqueda

```sql
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
```

**Resultado:**

| esquema | tabla | columna | collation |
| --- | --- | --- | --- |
| MDM | Catalogo_Variedades | Breeder | Modern_Spanish_CI_AS |
| MDM | Catalogo_Variedades | Nombre_Canonico | Modern_Spanish_CI_AS |
| Silver | Dim_Cama_Catalogo | Cama_Normalizada | Modern_Spanish_CI_AS |
| Silver | Dim_Fundo_Catalogo | Fundo | Modern_Spanish_CI_AS |
| Silver | Dim_Personal | DNI | Modern_Spanish_CI_AS |
| Silver | Dim_Personal | ID_Planilla | Modern_Spanish_CI_AS |
| Silver | Dim_Personal | Nombre_Completo | Modern_Spanish_CI_AS |
| Silver | Dim_Personal | Rol | Modern_Spanish_CI_AS |
| Silver | Dim_Sector_Catalogo | Sector | Modern_Spanish_CI_AS |
| Silver | Dim_Valvula_Catalogo | Valvula | Modern_Spanish_CI_AS |
| Silver | Dim_Variedad | Breeder | Modern_Spanish_CI_AS |
| Silver | Dim_Variedad | Nombre_Variedad | Modern_Spanish_CI_AS |

_Interpretación: una collation que termina en `_CI_AI` es case-insensitive_ _+ accent-insensitive — `LIKE '%garcia%'` SÍ matchea 'García'._ _Si termina en `_CI_AS` o `_CS_AS`, hay que normalizar con `COLLATE` o búsquedas como 'García' fallarán._


## 3. Cardinalidad de los facets

### Cuántos valores distintos hay por facet

```sql
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
```

**Resultado:**

| facet | valores_distintos |
| --- | --- |
| Silver.Dim_Variedad / Breeder | 18 |
| MDM.Catalogo_Variedades / Breeder | 1 |
| Silver.Dim_Personal / Rol | 3 |
| Silver.Dim_Fundo_Catalogo / Fundo | 2 |
| Silver.Dim_Sector_Catalogo / Sector | 8 |

_Interpretación: si valores_distintos <= 20, hardcodear el dropdown_ _es razonable (ahorra endpoint). Si > 50, requiere endpoint dedicado._


## 4. Top valores por facet (sample)

### Top 10 breeders (Silver.Dim_Variedad)

```sql
SELECT TOP 10
                ISNULL(Breeder, '_(null)_') AS breeder, COUNT(*) AS variedades
            FROM Silver.Dim_Variedad WITH (NOLOCK)
            GROUP BY Breeder
            ORDER BY 2 DESC
```

**Resultado:**

| breeder | variedades |
| --- | --- |
| FALL CREEK | 23 |
| POR_DEFINIR | 20 |
| _(null)_ | 17 |
| OZ BLUE | 9 |
| DRISCOLL | 9 |
| Pendiente MDM | 8 |
| IQ BERRIES | 6 |
| University of Florida | 6 |
| PLANASA | 5 |
| ACP I+D | 4 |

### Top 10 roles (Silver.Dim_Personal)

```sql
SELECT TOP 10
                ISNULL(Rol, '_(null)_') AS rol, COUNT(*) AS personas
            FROM Silver.Dim_Personal WITH (NOLOCK)
            GROUP BY Rol
            ORDER BY 2 DESC
```

**Resultado:**

| rol | personas |
| --- | --- |
| Evaluador | 230 |
| Sin Asignar | 1 |
| Operario | 1 |


---

**Próximos pasos sugeridos según resultados:**

- Si todos los catálogos están <2000 filas y collation es `_CI_AI`:
  **No migrar** — el cliente filtra perfecto. Confirmar TruncationWarning como red de seguridad.
- Si alguno supera 5000 filas o la collation es `_AS` (accent-sensitive):
  Migrar SOLO ese catálogo. Substring `LIKE '%x%'` + facets en payload.
- Si los facets de baja cardinalidad (<20): hardcodear en el cliente. Si altos: endpoint dedicado.
