-- =============================================================================
-- fase55_diagnostico_estado_carga_cosecha_sap.sql
-- =============================================================================
-- Objetivo (Bug 4):
--   Bronce.Cosecha_SAP tiene 473,763 filas con Estado_Carga != 'CARGADO'.
--   El procesador (ProcesadorCosechaHistorico) lee solo Estado_Carga='CARGADO'
--   y por eso esas filas quedan huerfanas.
--
-- Acciones (READ-ONLY salvo seccion 5 opcional):
--   1. Distribucion completa de Estado_Carga en Bronce.Cosecha_SAP.
--   2. Muestreo de filas por cada estado distinto.
--   3. Verificar si el "estado real" del cargador es algun string variante
--      (espacios, mayusculas, valores numericos como '1', etc).
--   4. Conteo de filas que SI deberian ser elegibles (sin filtro de estado).
--   5. (Opcional, comentado) Normalizar el campo Estado_Carga.
--
-- Pre-requisito: ninguno.
-- =============================================================================
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF OBJECT_ID('Bronce.Cosecha_SAP', 'U') IS NULL
BEGIN
    RAISERROR('Bronce.Cosecha_SAP no existe.', 16, 1);
    RETURN;
END;
GO

PRINT '=== 1. Distribucion completa de Estado_Carga ===';
SELECT
    Estado_Carga_Raw = ISNULL('[' + Estado_Carga + ']', '[NULL]'),
    Longitud         = LEN(Estado_Carga),
    Filas            = COUNT(*),
    Min_ID           = MIN(ID_Cosecha_SAP),
    Max_ID           = MAX(ID_Cosecha_SAP)
  FROM Bronce.Cosecha_SAP
 GROUP BY Estado_Carga
 ORDER BY COUNT(*) DESC;
GO

PRINT '=== 2. Caracteres no imprimibles / variantes en Estado_Carga ===';
SELECT TOP 20
    Estado_Carga_Hex  = CONVERT(VARBINARY(50), Estado_Carga),
    Estado_Carga_Text = Estado_Carga,
    Filas             = COUNT(*)
  FROM Bronce.Cosecha_SAP
 GROUP BY Estado_Carga
 ORDER BY COUNT(*) DESC;
GO

PRINT '=== 3. Muestra de filas POR cada estado distinto ===';
-- Nota: Bronce.Cosecha_SAP no tiene columna Fecha_Carga — se elimino de la consulta.
;WITH N AS (
    SELECT
        ID_Cosecha_SAP, Estado_Carga,
        ROW_NUMBER() OVER (PARTITION BY Estado_Carga ORDER BY ID_Cosecha_SAP) AS rn
      FROM Bronce.Cosecha_SAP
)
SELECT ID_Cosecha_SAP, Estado_Carga
  FROM N
 WHERE rn <= 3
 ORDER BY Estado_Carga, ID_Cosecha_SAP;
GO

PRINT '=== 4. Filas elegibles si normalizaramos Estado_Carga ===';
SELECT
    Total_Bronce         = COUNT(*),
    Carga_Estricto       = SUM(CASE WHEN Estado_Carga = 'CARGADO' THEN 1 ELSE 0 END),
    Carga_Trim_Upper     = SUM(CASE WHEN UPPER(LTRIM(RTRIM(Estado_Carga))) = 'CARGADO' THEN 1 ELSE 0 END),
    Es_NULL              = SUM(CASE WHEN Estado_Carga IS NULL THEN 1 ELSE 0 END),
    Es_Vacio             = SUM(CASE WHEN LTRIM(RTRIM(ISNULL(Estado_Carga,''))) = '' THEN 1 ELSE 0 END),
    Como_Numero_Uno      = SUM(CASE WHEN LTRIM(RTRIM(ISNULL(Estado_Carga,''))) = '1' THEN 1 ELSE 0 END),
    Procesado            = SUM(CASE WHEN UPPER(LTRIM(RTRIM(Estado_Carga))) = 'PROCESADO' THEN 1 ELSE 0 END),
    Rechazado            = SUM(CASE WHEN UPPER(LTRIM(RTRIM(Estado_Carga))) = 'RECHAZADO' THEN 1 ELSE 0 END)
  FROM Bronce.Cosecha_SAP;
GO

PRINT '=== 5. (Opcional, manual) Normalizar Estado_Carga ===';
PRINT '-- Descomentar despues de revisar la salida de la seccion 4.';
PRINT '-- UPDATE Bronce.Cosecha_SAP';
PRINT '--    SET Estado_Carga = ''PENDIENTE''';
PRINT '--  WHERE (Estado_Carga IS NULL';
PRINT '--      OR LTRIM(RTRIM(Estado_Carga)) IN ('''','' ''))';
PRINT '--    AND ID_Cosecha_SAP > 0;';
GO

PRINT 'fase55: diagnostico Estado_Carga Bronce.Cosecha_SAP completado.';
GO
