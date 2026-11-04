/*
================================================================================
 Refactor Silver.Fact_* (2026-05-20)  -- post refactor Bronce
 Idempotente, transaccional.
 C. Fact_Evaluacion_Pesos       -> renames
 D. Fact_Induccion_Floral       -> drop Codigo_Consumidor
 E. Fact_Tasa_Crecimiento_Brotes -> drop 8 cols + add Planta_Brote/Cantidad
================================================================================
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;
BEGIN TRY
BEGIN TRAN;

/* ==== C. Fact_Evaluacion_Pesos ==== */
IF OBJECT_ID('Silver.vFact_Evaluacion_Pesos','V') IS NOT NULL
    DROP VIEW Silver.vFact_Evaluacion_Pesos;

IF COL_LENGTH('Silver.Fact_Evaluacion_Pesos','Cantidad_Bayas_Muestra') IS NOT NULL
   AND COL_LENGTH('Silver.Fact_Evaluacion_Pesos','Cantidad_Cosechables') IS NULL
    EXEC sp_rename 'Silver.Fact_Evaluacion_Pesos.Cantidad_Bayas_Muestra',
                   'Cantidad_Cosechables', 'COLUMN';

IF COL_LENGTH('Silver.Fact_Evaluacion_Pesos','Peso_Proyectado_Baya_g') IS NOT NULL
   AND COL_LENGTH('Silver.Fact_Evaluacion_Pesos','Peso_Cosechables_g') IS NULL
    EXEC sp_rename 'Silver.Fact_Evaluacion_Pesos.Peso_Proyectado_Baya_g',
                   'Peso_Cosechables_g', 'COLUMN';

PRINT '[C] Fact_Evaluacion_Pesos renames OK';

/* ==== D. Fact_Induccion_Floral ==== */
IF OBJECT_ID('Silver.vFact_Induccion_Floral','V') IS NOT NULL
    DROP VIEW Silver.vFact_Induccion_Floral;

-- El indice unico de grano incluye Codigo_Consumidor; dropearlo primero
IF EXISTS (SELECT 1 FROM sys.indexes
           WHERE object_id = OBJECT_ID('Silver.Fact_Induccion_Floral')
             AND name = 'UX_Fact_InducFloral_Grain')
    DROP INDEX UX_Fact_InducFloral_Grain ON Silver.Fact_Induccion_Floral;

IF COL_LENGTH('Silver.Fact_Induccion_Floral','Codigo_Consumidor') IS NOT NULL
    ALTER TABLE Silver.Fact_Induccion_Floral DROP COLUMN Codigo_Consumidor;

-- Recrear indice unico sin Codigo_Consumidor (grano natural restante)
IF NOT EXISTS (SELECT 1 FROM sys.indexes
               WHERE object_id = OBJECT_ID('Silver.Fact_Induccion_Floral')
                 AND name = 'UX_Fact_InducFloral_Grain')
    CREATE UNIQUE INDEX UX_Fact_InducFloral_Grain
        ON Silver.Fact_Induccion_Floral
           (ID_Geografia, ID_Tiempo, ID_Variedad, ID_Personal, Tipo_Evaluacion);

PRINT '[D] Fact_Induccion_Floral drop Codigo_Consumidor + recreate index OK';

/* ==== E. Fact_Tasa_Crecimiento_Brotes ==== */
IF OBJECT_ID('Silver.vFact_Tasa_Crecimiento_Brotes','V') IS NOT NULL
    DROP VIEW Silver.vFact_Tasa_Crecimiento_Brotes;

-- Dropear indices y check constraints que dependen de cols a eliminar
IF EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('Silver.Fact_Tasa_Crecimiento_Brotes') AND name='IX_Fact_TasaCrecimiento_Ensayo')
    DROP INDEX IX_Fact_TasaCrecimiento_Ensayo ON Silver.Fact_Tasa_Crecimiento_Brotes;
IF EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('Silver.Fact_Tasa_Crecimiento_Brotes') AND name='UX_Fact_TCBrotes_Grain')
    DROP INDEX UX_Fact_TCBrotes_Grain ON Silver.Fact_Tasa_Crecimiento_Brotes;
IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE parent_object_id=OBJECT_ID('Silver.Fact_Tasa_Crecimiento_Brotes') AND name='CK_Fact_TasaCrecimiento_Medida')
    ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes DROP CONSTRAINT CK_Fact_TasaCrecimiento_Medida;
IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE parent_object_id=OBJECT_ID('Silver.Fact_Tasa_Crecimiento_Brotes') AND name='CK_Fact_TasaCrecimiento_DiasPoda')
    ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes DROP CONSTRAINT CK_Fact_TasaCrecimiento_DiasPoda;
IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE parent_object_id=OBJECT_ID('Silver.Fact_Tasa_Crecimiento_Brotes') AND name='CK_Fact_TasaCrecimiento_Ensayo')
    ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes DROP CONSTRAINT CK_Fact_TasaCrecimiento_Ensayo;

IF COL_LENGTH('Silver.Fact_Tasa_Crecimiento_Brotes','Condicion')          IS NOT NULL ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes DROP COLUMN Condicion;
IF COL_LENGTH('Silver.Fact_Tasa_Crecimiento_Brotes','Codigo_Ensayo')      IS NOT NULL ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes DROP COLUMN Codigo_Ensayo;
IF COL_LENGTH('Silver.Fact_Tasa_Crecimiento_Brotes','Codigo_Origen')      IS NOT NULL ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes DROP COLUMN Codigo_Origen;
IF COL_LENGTH('Silver.Fact_Tasa_Crecimiento_Brotes','Campana')            IS NOT NULL ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes DROP COLUMN Campana;
IF COL_LENGTH('Silver.Fact_Tasa_Crecimiento_Brotes','Observacion')        IS NOT NULL ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes DROP COLUMN Observacion;
IF COL_LENGTH('Silver.Fact_Tasa_Crecimiento_Brotes','Fecha_Poda_Aux')     IS NOT NULL ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes DROP COLUMN Fecha_Poda_Aux;
IF COL_LENGTH('Silver.Fact_Tasa_Crecimiento_Brotes','Dias_Desde_Poda')    IS NOT NULL ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes DROP COLUMN Dias_Desde_Poda;
IF COL_LENGTH('Silver.Fact_Tasa_Crecimiento_Brotes','Medida_Crecimiento') IS NOT NULL ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes DROP COLUMN Medida_Crecimiento;

IF COL_LENGTH('Silver.Fact_Tasa_Crecimiento_Brotes','Planta_Brote') IS NULL
    ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes ADD Planta_Brote NVARCHAR(50) NULL;
IF COL_LENGTH('Silver.Fact_Tasa_Crecimiento_Brotes','Cantidad') IS NULL
    ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes ADD Cantidad INT NULL;

-- Recrear indice unico de grano (sin cols dropeadas). EXEC para diferir
-- la validacion de Planta_Brote (recien agregada en este mismo batch).
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('Silver.Fact_Tasa_Crecimiento_Brotes') AND name='UX_Fact_TCBrotes_Grain')
    EXEC sp_executesql N'
        CREATE UNIQUE INDEX UX_Fact_TCBrotes_Grain
            ON Silver.Fact_Tasa_Crecimiento_Brotes
               (ID_Geografia, ID_Tiempo, ID_Variedad, ID_Personal, Tipo_Tallo, Estado_Vegetativo, Planta_Brote)
            WHERE Planta_Brote IS NOT NULL;
    ';

PRINT '[E] Fact_Tasa_Crecimiento_Brotes drop 8 + add 2 + recreate index OK';

COMMIT TRAN;
PRINT '======== DDL Silver COMPLETO (vistas se recrean despues) ========';
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRAN;
    DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
    PRINT '======== ERROR -> ROLLBACK ========';
    PRINT @msg;
    THROW;
END CATCH;
GO

/* ============================================================
   Recreacion de vistas (fuera de la transaccion, batch separado)
   ============================================================ */
CREATE OR ALTER VIEW Silver.vFact_Evaluacion_Pesos AS
SELECT
    f.ID_Evaluacion_Pesos, f.Fecha_Evento,
    fundo.Fundo, sector.Sector, modulo.Modulo, modulo.SubModulo,
    turno.Turno, valvula.Valvula, cama.Cama_Normalizada AS Cama,
    var.Nombre_Variedad AS Variedad,
    per.Nombre_Completo AS Evaluador, per.DNI AS Evaluador_DNI,
    f.Peso_Promedio_Baya_g,
    f.Cantidad_Cosechables,
    f.Peso_Cosechables_g,
    c_camp.Nombre_Campana AS Campana, f.Fecha_Sistema, f.Estado_DQ
FROM Silver.Fact_Evaluacion_Pesos f
JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo   fundo   ON geo.ID_Fundo_Catalogo   = fundo.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo  sector  ON geo.ID_Sector_Catalogo  = sector.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo  modulo  ON geo.ID_Modulo_Catalogo  = modulo.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo   turno   ON geo.ID_Turno_Catalogo   = turno.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo    cama    ON geo.ID_Cama_Catalogo    = cama.ID_Cama_Catalogo
LEFT JOIN Silver.Dim_Variedad         var     ON f.ID_Variedad           = var.ID_Variedad
LEFT JOIN Silver.Dim_Personal         per     ON f.ID_Personal           = per.ID_Personal
LEFT JOIN Silver.Dim_Campana          c_camp  ON f.ID_Campana            = c_camp.ID_Campana;
GO

CREATE OR ALTER VIEW Silver.vFact_Induccion_Floral AS
SELECT
    f.ID_Induccion_Floral, f.Fecha_Evento,
    fundo.Fundo, sector.Sector, modulo.Modulo, modulo.SubModulo,
    turno.Turno, valvula.Valvula, cama.Cama_Normalizada AS Cama,
    var.Nombre_Variedad AS Variedad,
    per.Nombre_Completo AS Evaluador, per.DNI AS Evaluador_DNI,
    f.Tipo_Evaluacion,
    f.Cantidad_Plantas_Por_Cama, f.Cantidad_Plantas_Con_Induccion,
    f.Cantidad_Brotes_Con_Induccion, f.Cantidad_Brotes_Totales, f.Cantidad_Brotes_Con_Flor,
    f.Pct_Plantas_Con_Induccion, f.Pct_Brotes_Con_Induccion, f.Pct_Brotes_Con_Flor,
    c_camp.Nombre_Campana AS Campana, f.Fecha_Sistema, f.Estado_DQ
FROM Silver.Fact_Induccion_Floral f
JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo   fundo   ON geo.ID_Fundo_Catalogo   = fundo.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo  sector  ON geo.ID_Sector_Catalogo  = sector.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo  modulo  ON geo.ID_Modulo_Catalogo  = modulo.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo   turno   ON geo.ID_Turno_Catalogo   = turno.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo    cama    ON geo.ID_Cama_Catalogo    = cama.ID_Cama_Catalogo
LEFT JOIN Silver.Dim_Variedad         var     ON f.ID_Variedad           = var.ID_Variedad
LEFT JOIN Silver.Dim_Personal         per     ON f.ID_Personal           = per.ID_Personal
LEFT JOIN Silver.Dim_Campana          c_camp  ON f.ID_Campana            = c_camp.ID_Campana;
GO

CREATE OR ALTER VIEW Silver.vFact_Tasa_Crecimiento_Brotes AS
SELECT
    f.ID_Tasa_Crecimiento_Brotes, f.Fecha_Evento,
    fundo.Fundo, sector.Sector, modulo.Modulo, modulo.SubModulo,
    turno.Turno, valvula.Valvula, cama.Cama_Normalizada AS Cama,
    var.Nombre_Variedad AS Variedad,
    per.Nombre_Completo AS Evaluador, per.DNI AS Evaluador_DNI,
    f.Tipo_Evaluacion, f.Estado_Vegetativo, f.Tipo_Tallo,
    f.Planta_Brote, f.Cantidad,
    c_camp.Nombre_Campana AS Campana, f.Fecha_Sistema, f.Estado_DQ
FROM Silver.Fact_Tasa_Crecimiento_Brotes f
JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo   fundo   ON geo.ID_Fundo_Catalogo   = fundo.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo  sector  ON geo.ID_Sector_Catalogo  = sector.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo  modulo  ON geo.ID_Modulo_Catalogo  = modulo.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo   turno   ON geo.ID_Turno_Catalogo   = turno.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo    cama    ON geo.ID_Cama_Catalogo    = cama.ID_Cama_Catalogo
LEFT JOIN Silver.Dim_Variedad         var     ON f.ID_Variedad           = var.ID_Variedad
LEFT JOIN Silver.Dim_Personal         per     ON f.ID_Personal           = per.ID_Personal
LEFT JOIN Silver.Dim_Campana          c_camp  ON f.ID_Campana            = c_camp.ID_Campana;
GO
