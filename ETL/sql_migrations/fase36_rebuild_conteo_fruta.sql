-- ============================================================================
-- fase36_rebuild_conteo_fruta.sql
-- ============================================================================
-- Adapta la tabla Bronce.Conteo_Fruta a la estructura ancha del nuevo excel.
-- Conserva las columnas anteriores por retrocompatibilidad.
-- ============================================================================

IF COL_LENGTH('Bronce.Conteo_Fruta', 'Punto_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta ADD Punto_Raw NVARCHAR(50) NULL;

IF COL_LENGTH('Bronce.Conteo_Fruta', 'BotonesFlorales_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta ADD BotonesFlorales_Raw NVARCHAR(50) NULL;

IF COL_LENGTH('Bronce.Conteo_Fruta', 'Flores_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta ADD Flores_Raw NVARCHAR(50) NULL;

IF COL_LENGTH('Bronce.Conteo_Fruta', 'BayasPequenas_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta ADD BayasPequenas_Raw NVARCHAR(50) NULL;

IF COL_LENGTH('Bronce.Conteo_Fruta', 'BayasGrandes_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta ADD BayasGrandes_Raw NVARCHAR(50) NULL;

IF COL_LENGTH('Bronce.Conteo_Fruta', 'Fase1_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta ADD Fase1_Raw NVARCHAR(50) NULL;

IF COL_LENGTH('Bronce.Conteo_Fruta', 'Fase2_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta ADD Fase2_Raw NVARCHAR(50) NULL;

IF COL_LENGTH('Bronce.Conteo_Fruta', 'BayasCremas_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta ADD BayasCremas_Raw NVARCHAR(50) NULL;

IF COL_LENGTH('Bronce.Conteo_Fruta', 'BayasMaduras_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta ADD BayasMaduras_Raw NVARCHAR(50) NULL;

IF COL_LENGTH('Bronce.Conteo_Fruta', 'BayasCosechables_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta ADD BayasCosechables_Raw NVARCHAR(50) NULL;

IF COL_LENGTH('Bronce.Conteo_Fruta', 'YemasActivadas_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta ADD YemasActivadas_Raw NVARCHAR(50) NULL;

IF COL_LENGTH('Bronce.Conteo_Fruta', 'PlantasProductivas_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta ADD PlantasProductivas_Raw NVARCHAR(50) NULL;

IF COL_LENGTH('Bronce.Conteo_Fruta', 'PlantasNoProductivas_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta ADD PlantasNoProductivas_Raw NVARCHAR(50) NULL;

IF COL_LENGTH('Bronce.Conteo_Fruta', 'Muestras_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta ADD Muestras_Raw NVARCHAR(50) NULL;

IF COL_LENGTH('Bronce.Conteo_Fruta', 'DNI_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta ADD DNI_Raw NVARCHAR(50) NULL;

IF COL_LENGTH('Bronce.Conteo_Fruta', 'Nombres_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta ADD Nombres_Raw NVARCHAR(150) NULL;

IF COL_LENGTH('Bronce.Conteo_Fruta', 'Fecha_Subida_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta ADD Fecha_Subida_Raw NVARCHAR(50) NULL;

PRINT 'Tabla Bronce.Conteo_Fruta adaptada exitosamente con las nuevas columnas del Excel.';
GO
