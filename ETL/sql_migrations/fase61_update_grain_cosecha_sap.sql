-- SQL Migration: Update uniqueness index for Silver.Fact_Cosecha_SAP to include Kg_Neto_MP
PRINT '== Re-creating UX_Fact_CosechaSAP_Grain to include Kg_Neto_MP ==';

IF EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Fact_CosechaSAP_Grain' AND object_id=OBJECT_ID('[Silver].[Fact_Cosecha_SAP]'))
BEGIN
    DROP INDEX [UX_Fact_CosechaSAP_Grain] ON [Silver].[Fact_Cosecha_SAP];
    PRINT '  Dropped old index UX_Fact_CosechaSAP_Grain';
END

CREATE UNIQUE NONCLUSTERED INDEX [UX_Fact_CosechaSAP_Grain] 
ON [Silver].[Fact_Cosecha_SAP] ([ID_Geografia], [ID_Tiempo], [ID_Variedad], [ID_Condicion_Cultivo], [Kg_Neto_MP]);
PRINT '  Created new unique index UX_Fact_CosechaSAP_Grain with Kg_Neto_MP';
