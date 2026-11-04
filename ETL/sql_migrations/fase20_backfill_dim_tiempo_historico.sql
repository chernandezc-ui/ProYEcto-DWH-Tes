-- =============================================================================
-- fase20_backfill_dim_tiempo_historico.sql
-- Backfill idempotente de Silver.Dim_Tiempo para historico operativo.
--
-- Objetivo:
--   cubrir fechas historicas de clima y otros dominios ya aceptadas por el ETL
--   sin duplicar filas existentes.
--
-- Uso:
--   1. Abrir en SSMS sobre la base correcta
--   2. Ejecutar completo
-- =============================================================================

SET NOCOUNT ON;
DECLARE @Fecha_Inicio DATE = '2020-01-01';
DECLARE @Fecha_Fin    DATE = '2026-06-30';

IF OBJECT_ID(N'Silver.Dim_Tiempo', N'U') IS NULL
BEGIN
    THROW 50001, 'No existe Silver.Dim_Tiempo en la base actual.', 1;
END;

PRINT 'Backfill Silver.Dim_Tiempo...';

;WITH fechas AS (
    SELECT @Fecha_Inicio AS fecha
    UNION ALL
    SELECT DATEADD(DAY, 1, fecha)
    FROM fechas
    WHERE fecha < @Fecha_Fin
)
INSERT INTO Silver.Dim_Tiempo (
    ID_Tiempo,
    Fecha,
    Anio,
    Mes,
    Semana_ISO,
    Semana_Cosecha,
    Dia_Semana,
    Nombre_Mes,
    Es_Fin_Semana
)
SELECT
    CAST(CONVERT(CHAR(8), fecha, 112) AS INT)    AS ID_Tiempo,
    fecha                                         AS Fecha,
    YEAR(fecha)                                   AS Anio,
    MONTH(fecha)                                  AS Mes,
    DATEPART(ISO_WEEK, fecha)                     AS Semana_ISO,
    DATEDIFF(WEEK, '2025-03-01', fecha) + 1       AS Semana_Cosecha,
    DATEPART(WEEKDAY, fecha)                      AS Dia_Semana,
    DATENAME(MONTH, fecha)                        AS Nombre_Mes,
    CASE WHEN DATEPART(WEEKDAY, fecha) IN (1, 7)
         THEN 1 ELSE 0 END                        AS Es_Fin_Semana
FROM fechas
WHERE NOT EXISTS (
    SELECT 1
    FROM Silver.Dim_Tiempo dt
    WHERE dt.ID_Tiempo = CAST(CONVERT(CHAR(8), fecha, 112) AS INT)
)
OPTION (MAXRECURSION 0);

PRINT 'Filas nuevas insertadas en Dim_Tiempo: ' + CAST(@@ROWCOUNT AS NVARCHAR(20));
GO

SELECT
    MIN(Fecha) AS Fecha_Minima,
    MAX(Fecha) AS Fecha_Maxima,
    COUNT(*)   AS Total_Filas
FROM Silver.Dim_Tiempo;
GO