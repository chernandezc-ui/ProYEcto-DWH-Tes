/* ============================================================================
   Limpieza de columnas redundantes en esquema Bronce
   Fecha   : 2026-05-19
   Autor   : ETL maintenance
   Contexto: 16 columnas verificadas como vacias (0 filas con dato) en tablas
             ya validadas a 0 filas totales. Riesgo de perdida = 0.
             Conteo_Fruta y Evaluacion_Vegetativa NO se tocan (tienen datos).
             Data_SAP queda fuera de esta migracion (analisis aparte).
   ============================================================================ */

USE ACP_DataWarehose_Proyecciones;
GO

SET XACT_ABORT ON;
BEGIN TRAN limpieza_bronce_redundantes;

/* ---------------------------------------------------------------------------
   GRUPO A: IDs nvarchar(MAX) redundantes sobre la PK bigint real
   --------------------------------------------------------------------------- */

-- Bronce.Consolidado_Tareos: conservar ID_Tareo (bigint PK)
ALTER TABLE Bronce.Consolidado_Tareos
    DROP COLUMN ID_Consolidado_Tareos;

-- Bronce.Evaluacion_Calidad_Poda: conservar ID_Evaluacion_Poda (bigint PK)
ALTER TABLE Bronce.Evaluacion_Calidad_Poda
    DROP COLUMN ID_Evaluacion_Calidad_Poda;

-- Bronce.Variables_Meteorologicas: conservar ID_Variables_Met (bigint PK)
ALTER TABLE Bronce.Variables_Meteorologicas
    DROP COLUMN ID_Variables_Meteorologicas;


/* ---------------------------------------------------------------------------
   GRUPO B: Evaluacion_Pesos - columnas legacy con encoding/acentos rotos
   Conservar las versiones normalizadas que escribe el cargador actual.
   --------------------------------------------------------------------------- */

ALTER TABLE Bronce.Evaluacion_Pesos
    DROP COLUMN
        [Fecha_de_evaluación_Raw],   -- reemplazada por Fecha_Raw
        [Fecha_de_subida_Raw],       -- reemplazada por Fecha_Subida_Raw
        [N°_cama_Raw],               -- reemplazada por Cama_Raw
        [Bayas_pequeñas_Raw],        -- reemplazada por BayasPequenas_Raw
        [Peso_bayas_pequeñas_Raw],   -- reemplazada por PesoBayasPequenas_Raw
        [Peso_bayas_pequeñas.1_Raw], -- reemplazada por PesoBayasPequenas2_Raw
        [Bayas_grandes_Raw],         -- reemplazada por BayasGrandes_Raw
        [Bayas_fase_1_Raw],          -- reemplazada por BayasFase1_Raw
        [Peso_bayas_fase_1_Raw],     -- reemplazada por PesoBayasFase1_Raw
        [Bayas_fase_2_Raw],          -- reemplazada por BayasFase2_Raw
        [Peso_bayas_fase_2_Raw],     -- reemplazada por PesoBayasFase2_Raw
        [Peso_cremas_Raw],           -- reemplazada por PesoCremas_Raw
        [Peso_maduras_Raw],          -- reemplazada por PesoMaduras_Raw
        [Peso_cosechables_Raw];      -- reemplazada por PesoCosechables_Raw


/* ---------------------------------------------------------------------------
   VERIFICACION post-drop
   --------------------------------------------------------------------------- */
SELECT TABLE_NAME, COUNT(*) AS columnas_finales
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'Bronce'
  AND TABLE_NAME IN (
      'Consolidado_Tareos',
      'Evaluacion_Calidad_Poda',
      'Variables_Meteorologicas',
      'Evaluacion_Pesos'
  )
GROUP BY TABLE_NAME
ORDER BY TABLE_NAME;


/* ---------------------------------------------------------------------------
   COMMIT manual: revisar resultados arriba y luego ejecutar:
       COMMIT TRAN limpieza_bronce_redundantes;
   o, si algo se ve mal:
       ROLLBACK TRAN limpieza_bronce_redundantes;
   --------------------------------------------------------------------------- */
