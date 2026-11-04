-- =============================================================================
-- fase46_dim_campana_seed_fechas.sql
-- =============================================================================
-- Objetivo (quirurgico, NO destructivo):
--   1. Backfill de fechas en Silver.Dim_Campana (11 filas existentes, sin tocar
--      Nombre_Campana ni ID_Campana ni UNIQUE).
--   2. Crear funcion MDM.fn_Resolver_ID_Campana que mapea cualquier texto
--      ("2024", "2024-2025", "2024 - 2025", "Campana 2024") -> ID_Campana
--      via Anio_Cosecha (el ANIO DE INICIO de la campana).
--
-- Convencion de campania (acordada con negocio):
--   "YYYY1 - YYYY2"  ->  Anio_Cosecha = YYYY1
--   Ej: "2021 - 2022" -> 2021. La etiqueta hereda el ANIO DE INICIO.
--
-- Fuentes del backfill (Data Historica + Vegetativa hist):
--   - BI_Cosecha3.xlsx              -> Fecha_Inicio_Campana, Fecha_Fin_Campana
--   - historico_vegetativa_*.xlsx   -> Fecha_Inicio_Poda, Fecha_Fin_Evaluacion
--
-- Idempotente: re-ejecutable. Los UPDATE solo aplican si la fecha actual difiere.
-- =============================================================================

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- -----------------------------------------------------------------------------
-- 0. Defensa: si por alguna razon las columnas no existieran, salimos limpio.
-- -----------------------------------------------------------------------------
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('Silver.Dim_Campana')
      AND name = 'Fecha_Inicio_Campana'
)
BEGIN
    RAISERROR('Silver.Dim_Campana no tiene las columnas de fechas esperadas. Abortando fase46.', 16, 1);
    RETURN;
END;
GO

-- -----------------------------------------------------------------------------
-- 1. Backfill por Anio_Cosecha (no toca filas que no existan; UPDATE puro)
--    NULL en Poda/Eval para anios sin datos en vegetativa hist.
--    NULL en Fecha_Fin_Campana para campanias en curso.
-- -----------------------------------------------------------------------------
;WITH SeedFechas AS (
    SELECT * FROM (VALUES
    --   Anio  Poda_Inicio   Eval_Fin      Camp_Inicio   Camp_Fin       VigOp
        (2016, CAST(NULL AS DATE),       CAST(NULL AS DATE),       CAST('2016-07-26' AS DATE), CAST('2017-02-03' AS DATE), 0),
        (2017, NULL,                     NULL,                     '2017-06-20',                '2018-02-07',                0),
        (2018, NULL,                     NULL,                     '2018-05-04',                '2019-01-18',                0),
        (2019, NULL,                     NULL,                     '2019-05-30',                '2020-01-10',                0),
        (2020, NULL,                     NULL,                     '2020-06-11',                '2021-02-05',                0),
        (2021, NULL,                     NULL,                     '2021-06-24',                '2022-02-04',                0),
        (2022, '2021-12-13',              '2023-02-13',              '2022-04-28',                '2023-04-05',                0),
        (2023, NULL,                     NULL,                     '2023-04-10',                '2024-04-02',                0),
        (2024, '2024-01-22',              '2025-01-03',              '2024-02-21',                '2025-03-20',                0),
        (2025, '2024-12-08',              '2026-02-27',              '2025-01-02',                '2026-04-08',                1),
        (2026, '2025-11-21',              '2026-05-14',              '2025-12-31',                NULL,                       1)
    ) v(Anio, Poda_Inicio, Eval_Fin, Camp_Inicio, Camp_Fin, VigOp)
)
UPDATE dc
   SET dc.Fecha_Inicio_Poda     = s.Poda_Inicio,
       dc.Fecha_Fin_Evaluacion  = s.Eval_Fin,
       dc.Fecha_Inicio_Campana  = s.Camp_Inicio,
       dc.Fecha_Fin_Campana     = s.Camp_Fin,
       dc.Es_Vigente_Operacion  = s.VigOp
  FROM Silver.Dim_Campana dc
  JOIN SeedFechas s ON s.Anio = dc.Anio_Cosecha
 WHERE -- solo aplica si hay diferencia (idempotencia + auditabilidad)
       ISNULL(CONVERT(VARCHAR(10), dc.Fecha_Inicio_Poda, 23),'')    <> ISNULL(CONVERT(VARCHAR(10), s.Poda_Inicio, 23),'')
    OR ISNULL(CONVERT(VARCHAR(10), dc.Fecha_Fin_Evaluacion, 23),'') <> ISNULL(CONVERT(VARCHAR(10), s.Eval_Fin, 23),'')
    OR ISNULL(CONVERT(VARCHAR(10), dc.Fecha_Inicio_Campana, 23),'') <> ISNULL(CONVERT(VARCHAR(10), s.Camp_Inicio, 23),'')
    OR ISNULL(CONVERT(VARCHAR(10), dc.Fecha_Fin_Campana, 23),'')    <> ISNULL(CONVERT(VARCHAR(10), s.Camp_Fin, 23),'')
    OR dc.Es_Vigente_Operacion <> s.VigOp;

DECLARE @filas_backfill INT = @@ROWCOUNT;
PRINT CONCAT('fase46: filas actualizadas = ', @filas_backfill);
GO

-- -----------------------------------------------------------------------------
-- 2. Funcion resolver. Devuelve ID_Campana o NULL si no se puede resolver.
--    El llamador decide que hacer con NULL (cuarentena, default 0, etc.).
-- -----------------------------------------------------------------------------
CREATE OR ALTER FUNCTION MDM.fn_Resolver_ID_Campana (@Campana_Raw NVARCHAR(100))
RETURNS INT
WITH SCHEMABINDING
AS
BEGIN
    IF @Campana_Raw IS NULL RETURN NULL;

    DECLARE @txt   NVARCHAR(100) = LTRIM(RTRIM(@Campana_Raw));
    DECLARE @pos   INT           = PATINDEX('%[0-9][0-9][0-9][0-9]%', @txt);
    IF @pos = 0 RETURN NULL;

    DECLARE @anio  INT = TRY_CAST(SUBSTRING(@txt, @pos, 4) AS INT);
    IF @anio IS NULL RETURN NULL;

    -- Regla: el primer grupo de 4 digitos es el ANIO DE INICIO de la campana.
    -- "2024-2025", "2024 - 2025", "2024", "Campana 2024" -> Anio_Cosecha = 2024.
    RETURN (SELECT TOP 1 ID_Campana
              FROM Silver.Dim_Campana
             WHERE Anio_Cosecha = @anio);
END;
GO

-- -----------------------------------------------------------------------------
-- 3. Smoke tests (no falla el deploy si no resuelve; solo imprime).
-- -----------------------------------------------------------------------------
DECLARE @t1 INT = MDM.fn_Resolver_ID_Campana(N'2024');
DECLARE @t2 INT = MDM.fn_Resolver_ID_Campana(N'2024-2025');
DECLARE @t3 INT = MDM.fn_Resolver_ID_Campana(N'2024 - 2025');
DECLARE @t4 INT = MDM.fn_Resolver_ID_Campana(N'Campa' + NCHAR(0x00F1) + N'a 2024');
DECLARE @t5 INT = MDM.fn_Resolver_ID_Campana(N'basura sin numero');
DECLARE @t6 INT = MDM.fn_Resolver_ID_Campana(NULL);

PRINT CONCAT('Resolver "2024"            -> ', ISNULL(CAST(@t1 AS VARCHAR(10)), 'NULL'));
PRINT CONCAT('Resolver "2024-2025"       -> ', ISNULL(CAST(@t2 AS VARCHAR(10)), 'NULL'));
PRINT CONCAT('Resolver "2024 - 2025"     -> ', ISNULL(CAST(@t3 AS VARCHAR(10)), 'NULL'));
PRINT CONCAT('Resolver "Campania 2024"   -> ', ISNULL(CAST(@t4 AS VARCHAR(10)), 'NULL'));
PRINT CONCAT('Resolver "basura..."       -> ', ISNULL(CAST(@t5 AS VARCHAR(10)), 'NULL (esperado)'));
PRINT CONCAT('Resolver NULL              -> ', ISNULL(CAST(@t6 AS VARCHAR(10)), 'NULL (esperado)'));
GO

-- -----------------------------------------------------------------------------
-- 4. Snapshot del resultado (revisar antes de aprobar fase47).
-- -----------------------------------------------------------------------------
SELECT ID_Campana, Anio_Cosecha, Nombre_Campana,
       Fecha_Inicio_Poda, Fecha_Fin_Evaluacion,
       Fecha_Inicio_Campana, Fecha_Fin_Campana,
       Es_Vigente_Operacion
  FROM Silver.Dim_Campana
 ORDER BY Anio_Cosecha;
GO
