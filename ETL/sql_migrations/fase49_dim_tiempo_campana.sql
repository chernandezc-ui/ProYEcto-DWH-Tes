-- ==============================================================================
-- FASE 49: Expandir Dim_Tiempo y Vincularla a Campaña
-- ==============================================================================
USE ACP_DataWarehose_Proyecciones;
GO

-- 1. Añadir columna ID_Campana a Dim_Tiempo
IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE Name = N'ID_Campana' AND Object_ID = Object_ID(N'Silver.Dim_Tiempo')
)
BEGIN
    ALTER TABLE Silver.Dim_Tiempo
    ADD ID_Campana INT NULL;

    -- FK a Dim_Campana
    ALTER TABLE Silver.Dim_Tiempo
    ADD CONSTRAINT FK_Dim_Tiempo_Campana 
    FOREIGN KEY (ID_Campana) REFERENCES Silver.Dim_Campana(ID_Campana);
END
GO

-- 2. Expandir Dim_Tiempo (Asegurar fechas desde 2015 hasta 2030)
DECLARE @StartDate DATE = '2015-01-01';
DECLARE @EndDate DATE = '2030-12-31';
DECLARE @CurrentDate DATE = @StartDate;

WHILE @CurrentDate <= @EndDate
BEGIN
    DECLARE @ID_Tiempo INT = CAST(CONVERT(VARCHAR(8), @CurrentDate, 112) AS INT);
    
    IF NOT EXISTS (SELECT 1 FROM Silver.Dim_Tiempo WHERE ID_Tiempo = @ID_Tiempo)
    BEGIN
        INSERT INTO Silver.Dim_Tiempo (
            ID_Tiempo, Fecha, Anio, Mes, Semana_ISO, Semana_Cosecha, 
            Dia_Semana, Nombre_Mes, Es_Fin_Semana
        )
        VALUES (
            @ID_Tiempo, 
            @CurrentDate, 
            YEAR(@CurrentDate), 
            MONTH(@CurrentDate), 
            DATEPART(ISO_WEEK, @CurrentDate),
            0, -- Semana_Cosecha (Dummy por ahora)
            DATEPART(WEEKDAY, @CurrentDate), 
            DATENAME(MONTH, @CurrentDate), 
            CASE WHEN DATEPART(WEEKDAY, @CurrentDate) IN (1, 7) THEN 1 ELSE 0 END
        );
    END
    SET @CurrentDate = DATEADD(DAY, 1, @CurrentDate);
END
GO

-- 3. Poblar ID_Campana utilizando la regla biológica
UPDATE t
SET t.ID_Campana = c.ID_Campana
FROM Silver.Dim_Tiempo t
CROSS APPLY (
    SELECT TOP 1 ID_Campana
    FROM Silver.Dim_Campana dc
    WHERE t.Fecha >= ISNULL(dc.Fecha_Inicio_Poda, DATEADD(month, -4, dc.Fecha_Inicio_Campana))
      AND t.Fecha <= ISNULL(dc.Fecha_Fin_Campana, '2099-12-31')
      AND dc.Es_Activa = 1
      AND dc.ID_Campana > 0
    ORDER BY dc.Anio_Cosecha DESC
) c;

-- Fechas fuera de campaña asignadas al ID_Campana = 0 (Sin Campaña)
UPDATE Silver.Dim_Tiempo
SET ID_Campana = 0
WHERE ID_Campana IS NULL;
GO
