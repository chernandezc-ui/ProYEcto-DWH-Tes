/* ==========================================================================
   fase64_columnas_bronce_faltantes.sql
   --------------------------------------------------------------------------
   El cargador Bronce alinea el DataFrame contra las columnas físicas de la
   tabla; cualquier columna del Excel que no exista como columna se descarta
   (o se empaca en Valores_Raw). Faltaban estas columnas, por eso datos que
   SÍ vienen en el Excel nunca llegaban a Bronce:

     - Bronce.Evaluacion_Calidad_Poda.Punto_Raw   (Excel trae 'Punto')
         -> el grano de Silver.Fact_Ciclo_Poda lo exige; sin él se cargaba 1%.
     - Bronce.Evaluacion_Pesos.Ano_Raw / Semana_Raw  (Excel trae 'Año','Semana')
         -> el reporte no trae fecha; se deriva de Año+Semana ISO en el fact.

   Tras aplicar: RECARGAR esas dos tablas Bronce desde el Excel para poblar
   las columnas nuevas (las filas actuales quedan con NULL hasta la recarga).
   ========================================================================== */
SET XACT_ABORT ON;

IF COL_LENGTH('Bronce.Evaluacion_Calidad_Poda', 'Punto_Raw') IS NULL
    ALTER TABLE Bronce.Evaluacion_Calidad_Poda ADD Punto_Raw NVARCHAR(100) NULL;
GO

IF COL_LENGTH('Bronce.Evaluacion_Pesos', 'Ano_Raw') IS NULL
    ALTER TABLE Bronce.Evaluacion_Pesos ADD Ano_Raw NVARCHAR(20) NULL;
GO

IF COL_LENGTH('Bronce.Evaluacion_Pesos', 'Semana_Raw') IS NULL
    ALTER TABLE Bronce.Evaluacion_Pesos ADD Semana_Raw NVARCHAR(20) NULL;
GO
