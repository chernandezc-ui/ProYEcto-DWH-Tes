/* =====================================================================
 fase37_bridges_tasa_crecimiento.sql
 ---------------------------------------------------------------------
 Modelado dimensional con bridges para Fact_Tasa_Crecimiento_Brotes:
   1) Bridge_Modulo_Campana gana columna ID_Condicion (FK Dim_Condicion).
   2) Fact_Tasa_Crecimiento_Brotes gana ID_Condicion + ID_Cama_Catalogo
      como FKs y deja de guardar Condicion/Campana como texto.
   3) Vista vw_Tasa_Crecimiento_Trazabilidad: union fact + bridges + dims.

 Estrategia transaccional:
   - DDL aplica inmediato (NULL inicial donde sea necesario).
   - Backfill ejecutado en bloques con auditoria.
   - Hardening (NOT NULL + DROP COLUMN) queda al final, comentado, para
     ejecutar manual una vez validado.
===================================================================== */

SET XACT_ABORT ON;
SET NOCOUNT ON;

BEGIN TRANSACTION;

-- ---------------------------------------------------------------------
-- 1) Semilla minima de Dim_Condicion_Cultivo (idempotente)
-- ---------------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM Silver.Dim_Condicion_Cultivo WHERE Sustrato = 'COCO' AND Certificacion = 'ORGANICO')
    INSERT INTO Silver.Dim_Condicion_Cultivo (Sustrato, Certificacion) VALUES ('COCO', 'ORGANICO');
IF NOT EXISTS (SELECT 1 FROM Silver.Dim_Condicion_Cultivo WHERE Sustrato = 'COCO' AND Certificacion = 'CONVENCIONAL')
    INSERT INTO Silver.Dim_Condicion_Cultivo (Sustrato, Certificacion) VALUES ('COCO', 'CONVENCIONAL');
IF NOT EXISTS (SELECT 1 FROM Silver.Dim_Condicion_Cultivo WHERE Sustrato = 'TIERRA' AND Certificacion = 'ORGANICO')
    INSERT INTO Silver.Dim_Condicion_Cultivo (Sustrato, Certificacion) VALUES ('TIERRA', 'ORGANICO');
IF NOT EXISTS (SELECT 1 FROM Silver.Dim_Condicion_Cultivo WHERE Sustrato = 'TIERRA' AND Certificacion = 'CONVENCIONAL')
    INSERT INTO Silver.Dim_Condicion_Cultivo (Sustrato, Certificacion) VALUES ('TIERRA', 'CONVENCIONAL');
IF NOT EXISTS (SELECT 1 FROM Silver.Dim_Condicion_Cultivo WHERE Sustrato = 'DESCONOCIDO' AND Certificacion = 'DESCONOCIDA')
    INSERT INTO Silver.Dim_Condicion_Cultivo (Sustrato, Certificacion) VALUES ('DESCONOCIDO', 'DESCONOCIDA');

-- ---------------------------------------------------------------------
-- 2) Bridge_Modulo_Campana: agregar ID_Condicion (NULLable inicial)
-- ---------------------------------------------------------------------
IF COL_LENGTH('Silver.Bridge_Modulo_Campana', 'ID_Condicion') IS NULL
BEGIN
    ALTER TABLE Silver.Bridge_Modulo_Campana ADD ID_Condicion INT NULL;
END;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_Bridge_Modulo_Campana_Condicion'
)
BEGIN
    ALTER TABLE Silver.Bridge_Modulo_Campana
        ADD CONSTRAINT FK_Bridge_Modulo_Campana_Condicion
        FOREIGN KEY (ID_Condicion) REFERENCES Silver.Dim_Condicion_Cultivo(ID_Condicion);
END;
GO

-- ---------------------------------------------------------------------
-- 3) Fact_Tasa_Crecimiento_Brotes: agregar ID_Condicion + ID_Cama_Catalogo
-- ---------------------------------------------------------------------
IF COL_LENGTH('Silver.Fact_Tasa_Crecimiento_Brotes', 'ID_Condicion') IS NULL
BEGIN
    ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes ADD ID_Condicion INT NULL;
END;
GO

IF COL_LENGTH('Silver.Fact_Tasa_Crecimiento_Brotes', 'ID_Cama_Catalogo') IS NULL
BEGIN
    ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes ADD ID_Cama_Catalogo INT NULL;
END;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_FactTasa_Condicion'
)
BEGIN
    ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes
        ADD CONSTRAINT FK_FactTasa_Condicion
        FOREIGN KEY (ID_Condicion) REFERENCES Silver.Dim_Condicion_Cultivo(ID_Condicion);
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_FactTasa_Cama'
)
BEGIN
    ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes
        ADD CONSTRAINT FK_FactTasa_Cama
        FOREIGN KEY (ID_Cama_Catalogo) REFERENCES Silver.Dim_Cama_Catalogo(ID_Cama_Catalogo);
END;
GO

-- ---------------------------------------------------------------------
-- 4) Backfill (revisar antes de ejecutar en producción)
-- ---------------------------------------------------------------------

-- 4.1 Backfill ID_Condicion del fact desde texto Condicion historico
--     Regla simple: cualquier match parcial. Ajustar segun datos reales.
UPDATE f
SET f.ID_Condicion = dc.ID_Condicion
FROM Silver.Fact_Tasa_Crecimiento_Brotes f
JOIN Silver.Dim_Condicion_Cultivo dc
  ON UPPER(LTRIM(RTRIM(ISNULL(f.Condicion, '')))) LIKE '%' + dc.Certificacion + '%'
WHERE f.ID_Condicion IS NULL
  AND f.Condicion IS NOT NULL
  AND dc.Sustrato = 'COCO';  -- supuesto: sustrato default = COCO. Cambiar si aplica.

-- Cuanto quedo sin mapear (visibilidad)
SELECT
    'fact_sin_condicion' AS metric,
    COUNT(*) AS filas
FROM Silver.Fact_Tasa_Crecimiento_Brotes
WHERE ID_Condicion IS NULL;

-- 4.2 Backfill ID_Cama_Catalogo del fact desde Bronce.Cama_Raw
--     Match por nombre normalizado en Dim_Cama_Catalogo.
UPDATE f
SET f.ID_Cama_Catalogo = dc.ID_Cama_Catalogo
FROM Silver.Fact_Tasa_Crecimiento_Brotes f
JOIN Bronce.Tasa_Crecimiento_Brotes b
  ON b.ID_Tasa_Crecimiento = f.ID_Tasa_Crecimiento_Brotes
JOIN Silver.Dim_Cama_Catalogo dc
  ON UPPER(LTRIM(RTRIM(ISNULL(b.Cama_Raw, '')))) = dc.Cama_Normalizada
WHERE f.ID_Cama_Catalogo IS NULL;

SELECT
    'fact_sin_cama' AS metric,
    COUNT(*) AS filas
FROM Silver.Fact_Tasa_Crecimiento_Brotes
WHERE ID_Cama_Catalogo IS NULL;

-- 4.3 Insertar filas faltantes en Bridge_Geografia_Cama para los pares
--     (Geo, Cama) que aparecen en el fact y no estan en el bridge.
INSERT INTO Silver.Bridge_Geografia_Cama
    (ID_Geografia, ID_Cama_Catalogo, Fecha_Inicio_Vigencia, Fecha_Fin_Vigencia,
     Es_Vigente, Fuente_Registro, Observacion)
SELECT DISTINCT
    f.ID_Geografia,
    f.ID_Cama_Catalogo,
    CAST('1900-01-01' AS DATE) AS Fecha_Inicio_Vigencia,
    NULL AS Fecha_Fin_Vigencia,
    1 AS Es_Vigente,
    'backfill_fase37' AS Fuente_Registro,
    'Inferido desde Fact_Tasa_Crecimiento_Brotes' AS Observacion
FROM Silver.Fact_Tasa_Crecimiento_Brotes f
WHERE f.ID_Cama_Catalogo IS NOT NULL
  AND NOT EXISTS (
        SELECT 1
        FROM Silver.Bridge_Geografia_Cama br
        WHERE br.ID_Geografia      = f.ID_Geografia
          AND br.ID_Cama_Catalogo  = f.ID_Cama_Catalogo
  );

-- 4.4 Backfill Bridge_Modulo_Campana.ID_Condicion con la condicion mayoritaria
--     observada por (ID_Modulo_Catalogo, ID_Variedad, ID_Campana) en el fact.
;WITH condicion_mayoritaria AS (
    SELECT
        g.ID_Modulo_Catalogo,
        f.ID_Variedad,
        f.ID_Campana,
        f.ID_Condicion,
        COUNT(*) AS filas,
        ROW_NUMBER() OVER (
            PARTITION BY g.ID_Modulo_Catalogo, f.ID_Variedad, f.ID_Campana
            ORDER BY COUNT(*) DESC
        ) AS rk
    FROM Silver.Fact_Tasa_Crecimiento_Brotes f
    JOIN Silver.Dim_Geografia g ON g.ID_Geografia = f.ID_Geografia
    WHERE f.ID_Condicion IS NOT NULL
      AND f.ID_Campana   IS NOT NULL
    GROUP BY g.ID_Modulo_Catalogo, f.ID_Variedad, f.ID_Campana, f.ID_Condicion
)
UPDATE bmc
SET bmc.ID_Condicion = cm.ID_Condicion
FROM Silver.Bridge_Modulo_Campana bmc
JOIN condicion_mayoritaria cm
  ON cm.rk = 1
 AND cm.ID_Modulo_Catalogo = bmc.ID_Modulo_Catalogo
 AND cm.ID_Variedad        = bmc.ID_Variedad
 AND cm.ID_Campana         = bmc.ID_Campana
WHERE bmc.ID_Condicion IS NULL;

SELECT
    'bridge_modulo_campana_sin_condicion' AS metric,
    COUNT(*) AS filas
FROM Silver.Bridge_Modulo_Campana
WHERE ID_Condicion IS NULL;

COMMIT TRANSACTION;
GO

-- ---------------------------------------------------------------------
-- 5) Vista de trazabilidad (CREATE OR ALTER, fuera de la transaccion DDL)
-- ---------------------------------------------------------------------
GO
CREATE OR ALTER VIEW Silver.vw_Tasa_Crecimiento_Trazabilidad AS
SELECT
    f.ID_Tasa_Crecimiento_Brotes,
    t.Fecha,
    mc.Modulo,
    tc.Codigo_Turno,
    vc.Codigo_Valvula,
    cc.Cama_Normalizada,
    v.Nombre_Variedad,
    ca.Nombre_Campana,
    cu.Sustrato,
    cu.Certificacion,
    f.Tipo_Tallo,
    f.Estado_Vegetativo,
    f.Codigo_Ensayo,
    f.Medida_Crecimiento,
    f.Dias_Desde_Poda,
    f.Fecha_Evento
FROM Silver.Fact_Tasa_Crecimiento_Brotes f
JOIN Silver.Dim_Tiempo t                ON t.ID_Tiempo = f.ID_Tiempo
JOIN Silver.Dim_Geografia g             ON g.ID_Geografia = f.ID_Geografia
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo tc  ON tc.ID_Turno_Catalogo  = g.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON vc.ID_Valvula_Catalogo = g.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo cc   ON cc.ID_Cama_Catalogo = f.ID_Cama_Catalogo
JOIN Silver.Dim_Variedad v              ON v.ID_Variedad = f.ID_Variedad
LEFT JOIN Silver.Dim_Campana ca         ON ca.ID_Campana = f.ID_Campana
LEFT JOIN Silver.Dim_Condicion_Cultivo cu ON cu.ID_Condicion = f.ID_Condicion;
GO

-- ---------------------------------------------------------------------
-- 6) Hardening (ejecutar SOLO despues de validar backfill 100%)
-- ---------------------------------------------------------------------
/*
ALTER TABLE Silver.Bridge_Modulo_Campana ALTER COLUMN ID_Condicion INT NOT NULL;
ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes ALTER COLUMN ID_Condicion INT NOT NULL;
ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes ALTER COLUMN ID_Cama_Catalogo INT NOT NULL;

-- Drop columnas texto crudo que ya estan capturadas por FKs:
ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes DROP COLUMN Condicion;
ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes DROP COLUMN Campana;
*/
