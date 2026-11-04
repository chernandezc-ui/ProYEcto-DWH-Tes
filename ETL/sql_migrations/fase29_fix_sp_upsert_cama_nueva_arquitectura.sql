-- =============================================================================
-- FASE 29: Actualizar Silver.sp_Upsert_Cama_Desde_Bronce para arquitectura
--          de catálogos geográficos.
--
-- Problema: El SP buscaba geografía con columnas planas (Modulo, SubModulo,
-- Turno, Valvula) directamente en Dim_Geografia. Esas columnas ya no existen
-- ahí — están en Dim_Modulo_Catalogo, Dim_Turno_Catalogo y Dim_Valvula_Catalogo,
-- vinculadas a Dim_Geografia a través de sus IDs de catálogo.
--
-- Cambio único: el OUTER APPLY que resuelve ID_Geografia ahora hace JOIN
-- a los tres catálogos. Todo lo demás del SP es idéntico al original.
-- =============================================================================

CREATE OR ALTER PROCEDURE Silver.sp_Upsert_Cama_Desde_Bronce
    @Modo_Aplicar       BIT = 0,
    @Cama_Min_Permitida INT = 1,
    @Cama_Max_Permitida INT = 100
AS
BEGIN
    SET NOCOUNT ON;

    IF OBJECT_ID('Silver.Dim_Cama_Catalogo', 'U') IS NULL
    BEGIN
        RAISERROR('No existe Silver.Dim_Cama_Catalogo.', 16, 1);
        RETURN;
    END;

    IF OBJECT_ID('Silver.Bridge_Geografia_Cama', 'U') IS NULL
    BEGIN
        RAISERROR('No existe Silver.Bridge_Geografia_Cama.', 16, 1);
        RETURN;
    END;

    IF OBJECT_ID('Bronce.Evaluacion_Pesos', 'U') IS NULL
       OR OBJECT_ID('Bronce.Evaluacion_Vegetativa', 'U') IS NULL
    BEGIN
        RAISERROR('No existen tablas Bronce requeridas.', 16, 1);
        RETURN;
    END;

    IF OBJECT_ID('tempdb..#BronceRaw') IS NOT NULL DROP TABLE #BronceRaw;
    IF OBJECT_ID('tempdb..#Eval')      IS NOT NULL DROP TABLE #Eval;
    IF OBJECT_ID('tempdb..#Aptos')     IS NOT NULL DROP TABLE #Aptos;

    -- ── 1. Leer último lote de cada fuente Bronce ─────────────────────────────
    CREATE TABLE #BronceRaw (
        Tabla_Origen NVARCHAR(50)  NOT NULL,
        Modulo_Raw   NVARCHAR(100) NULL,
        Turno_Raw    NVARCHAR(100) NULL,
        Valvula_Raw  NVARCHAR(100) NULL,
        Cama_Raw     NVARCHAR(100) NULL
    );

    ;WITH LotePesos AS (
        SELECT TOP (1) Fecha_Sistema, Nombre_Archivo
        FROM Bronce.Evaluacion_Pesos
        ORDER BY Fecha_Sistema DESC, ID_Evaluacion_Pesos DESC
    )
    INSERT INTO #BronceRaw (Tabla_Origen, Modulo_Raw, Turno_Raw, Valvula_Raw, Cama_Raw)
    SELECT 'Bronce.Evaluacion_Pesos', p.Modulo_Raw, p.Turno_Raw, p.Valvula_Raw, p.Cama_Raw
    FROM Bronce.Evaluacion_Pesos p
    INNER JOIN LotePesos l ON p.Fecha_Sistema = l.Fecha_Sistema
                          AND p.Nombre_Archivo = l.Nombre_Archivo;

    ;WITH LoteVeg AS (
        SELECT TOP (1) Fecha_Sistema, Nombre_Archivo
        FROM Bronce.Evaluacion_Vegetativa
        ORDER BY Fecha_Sistema DESC, ID_Evaluacion_Vegetativa DESC
    )
    INSERT INTO #BronceRaw (Tabla_Origen, Modulo_Raw, Turno_Raw, Valvula_Raw, Cama_Raw)
    SELECT 'Bronce.Evaluacion_Vegetativa', v.Modulo_Raw, v.Turno_Raw, v.Valvula_Raw, v.Cama_Raw
    FROM Bronce.Evaluacion_Vegetativa v
    INNER JOIN LoteVeg l ON v.Fecha_Sistema = l.Fecha_Sistema
                        AND v.Nombre_Archivo = l.Nombre_Archivo;

    -- ── 2. Resolver geografía por fila ────────────────────────────────────────
    CREATE TABLE #Eval (
        Estado_Resolucion NVARCHAR(50) NOT NULL,
        ID_Geografia      INT          NULL,
        Cama_Int          INT          NULL
    );

    INSERT INTO #Eval (Estado_Resolucion, ID_Geografia, Cama_Int)
    SELECT
        CASE
            WHEN x.Es_Modulo_Especial = 1                                                        THEN 'CASO_ESPECIAL_MODULO'
            WHEN x.Modulo_Int IS NULL OR x.Turno_Int IS NULL OR x.Valvula_Token IS NULL          THEN 'CLAVE_GEOGRAFICA_INCOMPLETA'
            WHEN x.Cama_Int IS NULL
              OR x.Cama_Int < @Cama_Min_Permitida
              OR x.Cama_Int > @Cama_Max_Permitida                                                THEN 'CAMA_NO_VALIDA'
            WHEN x.Coincidencias_Geo = 0                                                         THEN 'GEOGRAFIA_NO_ENCONTRADA'
            WHEN x.Coincidencias_Geo > 1                                                         THEN 'GEOGRAFIA_AMBIGUA'
            ELSE 'APTO_PARA_INSERT'
        END AS Estado_Resolucion,
        CASE WHEN x.Coincidencias_Geo = 1 THEN x.ID_Geografia_Unica ELSE NULL END AS ID_Geografia,
        x.Cama_Int
    FROM (
        SELECT
            t.Modulo_Int,
            t.SubModulo_Int,
            t.Turno_Int,
            t.Valvula_Token,
            t.Cama_Int,
            t.Es_Modulo_Especial,
            g.Coincidencias_Geo,
            g.ID_Geografia_Unica
        FROM #BronceRaw r
        CROSS APPLY (
            SELECT
                NULLIF(LTRIM(RTRIM(r.Modulo_Raw)),  '') AS Modulo_Token_Raw,
                NULLIF(LTRIM(RTRIM(r.Turno_Raw)),   '') AS Turno_Token_Raw,
                NULLIF(LTRIM(RTRIM(r.Valvula_Raw)), '') AS Valvula_Token_Raw,
                NULLIF(LTRIM(RTRIM(r.Cama_Raw)),    '') AS Cama_Token_Raw
        ) raw
        OUTER APPLY (
            SELECT TOP (1)
                rr.Modulo_Int,
                rr.SubModulo_Int,
                ISNULL(rr.Es_Test_Block, 0) AS Es_Test_Block_Regla
            FROM MDM.Regla_Modulo_Raw rr
            WHERE rr.Es_Activa = 1
              AND raw.Modulo_Token_Raw IS NOT NULL
              AND UPPER(LTRIM(RTRIM(rr.Modulo_Raw))) = UPPER(raw.Modulo_Token_Raw)
        ) regla
        CROSS APPLY (
            SELECT
                CASE WHEN raw.Turno_Token_Raw IS NULL   THEN NULL
                     WHEN raw.Turno_Token_Raw   NOT LIKE '%[^0-9]%' THEN CONVERT(INT, raw.Turno_Token_Raw)
                     ELSE NULL END AS Turno_Int,
                CASE WHEN raw.Valvula_Token_Raw IS NULL THEN NULL
                     WHEN raw.Valvula_Token_Raw NOT LIKE '%[^0-9]%' THEN CONVERT(NVARCHAR(50), CONVERT(INT, raw.Valvula_Token_Raw))
                     ELSE raw.Valvula_Token_Raw END AS Valvula_Token,
                CASE WHEN raw.Cama_Token_Raw IS NULL    THEN NULL
                     WHEN raw.Cama_Token_Raw    NOT LIKE '%[^0-9]%' THEN CONVERT(INT, raw.Cama_Token_Raw)
                     ELSE NULL END AS Cama_Int,
                CASE WHEN raw.Modulo_Token_Raw IS NOT NULL
                      AND raw.Modulo_Token_Raw NOT LIKE '%[^0-9]%' THEN CONVERT(INT, raw.Modulo_Token_Raw)
                     ELSE NULL END AS Modulo_Int_Raw
        ) base
        CROSS APPLY (
            SELECT
                COALESCE(regla.Modulo_Int, base.Modulo_Int_Raw)   AS Modulo_Int,
                regla.SubModulo_Int                                AS SubModulo_Int,
                CASE
                    WHEN ISNULL(regla.Es_Test_Block_Regla, 0) = 1           THEN 1
                    WHEN COALESCE(regla.Modulo_Int, base.Modulo_Int_Raw) IS NULL THEN 1
                    ELSE 0
                END AS Es_Modulo_Especial,
                base.Turno_Int,
                base.Valvula_Token,
                base.Cama_Int
        ) t
        -- ── CAMBIO RESPECTO AL SP ORIGINAL ────────────────────────────────────
        -- Antes: WHERE gv.Modulo = ... AND gv.SubModulo = ... AND gv.Turno = ... AND gv.Valvula = ...
        -- Ahora: JOIN a Dim_Modulo_Catalogo, Dim_Turno_Catalogo, Dim_Valvula_Catalogo
        OUTER APPLY (
            SELECT
                COUNT(*)          AS Coincidencias_Geo,
                MIN(gv.ID_Geografia) AS ID_Geografia_Unica
            FROM Silver.Dim_Geografia      gv
            JOIN Silver.Dim_Modulo_Catalogo  mc ON mc.ID_Modulo_Catalogo  = gv.ID_Modulo_Catalogo
            JOIN Silver.Dim_Turno_Catalogo   tc ON tc.ID_Turno_Catalogo   = gv.ID_Turno_Catalogo
            JOIN Silver.Dim_Valvula_Catalogo vc ON vc.ID_Valvula_Catalogo = gv.ID_Valvula_Catalogo
            WHERE ISNULL(gv.Es_Vigente,    1) = 1
              AND ISNULL(gv.Es_Test_Block,  0) = 0
              AND mc.Modulo                      = t.Modulo_Int
              AND ISNULL(mc.SubModulo, -1)       = ISNULL(t.SubModulo_Int, -1)
              AND tc.Turno                       = t.Turno_Int
              AND (
                    CASE
                        WHEN LTRIM(RTRIM(CONVERT(NVARCHAR(50), vc.Valvula))) = ''   THEN NULL
                        WHEN LTRIM(RTRIM(CONVERT(NVARCHAR(50), vc.Valvula))) NOT LIKE '%[^0-9]%'
                            THEN CONVERT(NVARCHAR(50), CONVERT(INT, LTRIM(RTRIM(CONVERT(NVARCHAR(50), vc.Valvula)))))
                        ELSE LTRIM(RTRIM(CONVERT(NVARCHAR(50), vc.Valvula)))
                    END
                  ) = t.Valvula_Token
        ) g
    ) x;

    -- ── 3. Filtrar aptos ──────────────────────────────────────────────────────
    CREATE TABLE #Aptos (
        ID_Geografia    INT          NOT NULL,
        Cama_Normalizada NVARCHAR(50) NOT NULL,
        CONSTRAINT PK_Aptos PRIMARY KEY (ID_Geografia, Cama_Normalizada)
    );

    INSERT INTO #Aptos (ID_Geografia, Cama_Normalizada)
    SELECT DISTINCT
        e.ID_Geografia,
        CONVERT(NVARCHAR(50), e.Cama_Int)
    FROM #Eval e
    WHERE e.Estado_Resolucion = 'APTO_PARA_INSERT'
      AND e.ID_Geografia IS NOT NULL
      AND e.Cama_Int BETWEEN @Cama_Min_Permitida AND @Cama_Max_Permitida;

    -- ── 4. Aplicar (solo si @Modo_Aplicar = 1) ────────────────────────────────
    DECLARE
        @Insert_Catalogo_Real INT = 0,
        @Insert_Bridge_Real   INT = 0;

    IF @Modo_Aplicar = 1
    BEGIN
        BEGIN TRANSACTION;

        INSERT INTO Silver.Dim_Cama_Catalogo (Cama_Normalizada)
        SELECT DISTINCT a.Cama_Normalizada
        FROM #Aptos a
        WHERE NOT EXISTS (
            SELECT 1 FROM Silver.Dim_Cama_Catalogo c
            WHERE c.Cama_Normalizada = a.Cama_Normalizada
        );
        SET @Insert_Catalogo_Real = @@ROWCOUNT;

        INSERT INTO Silver.Bridge_Geografia_Cama (
            ID_Geografia, ID_Cama_Catalogo,
            Fecha_Inicio_Vigencia, Fecha_Fin_Vigencia,
            Es_Vigente, Fuente_Registro, Observacion
        )
        SELECT
            a.ID_Geografia,
            c.ID_Cama_Catalogo,
            CAST(GETDATE() AS DATE),
            NULL,
            1,
            'SP_UPSERT_CAMA_BRONCE',
            'Insercion via Silver.sp_Upsert_Cama_Desde_Bronce'
        FROM #Aptos a
        INNER JOIN Silver.Dim_Cama_Catalogo c ON c.Cama_Normalizada = a.Cama_Normalizada
        WHERE NOT EXISTS (
            SELECT 1 FROM Silver.Bridge_Geografia_Cama b
            WHERE b.ID_Geografia    = a.ID_Geografia
              AND b.ID_Cama_Catalogo = c.ID_Cama_Catalogo
              AND b.Es_Vigente       = 1
              AND b.Fecha_Fin_Vigencia IS NULL
        );
        SET @Insert_Bridge_Real = @@ROWCOUNT;

        COMMIT TRANSACTION;
    END;

    -- ── 5. Resultados ─────────────────────────────────────────────────────────
    SELECT
        @Modo_Aplicar                           AS Modo_Aplicar,
        (SELECT COUNT(*) FROM #BronceRaw)       AS Filas_Bronce_Leidas,
        (SELECT COUNT(*) FROM #Eval)            AS Filas_Evaluadas,
        (SELECT COUNT(*) FROM #Aptos)           AS Combinaciones_Aptas_Distintas,
        @Insert_Catalogo_Real                   AS Insert_Catalogo_Real,
        @Insert_Bridge_Real                     AS Insert_Bridge_Real;

    SELECT Estado_Resolucion, COUNT(*) AS Filas
    FROM #Eval
    GROUP BY Estado_Resolucion
    ORDER BY COUNT(*) DESC;
END;
GO
