-- Migración: Hacer Peso_Promedio_Baya_g nullable en Silver.Fact_Evaluacion_Pesos
-- Razón: datos históricos (pre-2025) no traen Cosechables/PesoCosechables
-- en el Excel, así que el peso no puede calcularse y se inserta como NULL.
-- El índice IX_FactPesos_Gold_Cobertura debe dropearse, alterarse y recrearse.

-- 1. Drop índice dependiente
IF EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('Silver.Fact_Evaluacion_Pesos')
    AND name = 'IX_FactPesos_Gold_Cobertura'
)
    DROP INDEX [IX_FactPesos_Gold_Cobertura] ON [Silver].[Fact_Evaluacion_Pesos];

-- 2. Alterar columna a NULL
ALTER TABLE [Silver].[Fact_Evaluacion_Pesos]
    ALTER COLUMN [Peso_Promedio_Baya_g] DECIMAL(10,4) NULL;

-- 3. Recrear índice (sin la restricción NOT NULL implícita)
CREATE INDEX [IX_FactPesos_Gold_Cobertura]
    ON [Silver].[Fact_Evaluacion_Pesos] ([ID_Variedad], [ID_Tiempo])
    INCLUDE ([Peso_Promedio_Baya_g], [Cantidad_Cosechables]);

PRINT 'OK: Peso_Promedio_Baya_g es ahora nullable y IX_FactPesos_Gold_Cobertura recreado.';
