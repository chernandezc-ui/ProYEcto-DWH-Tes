/*
 ============================================================================
 2026_05_25_repair_post_fixes.sql
 ============================================================================
 Reparacion y re-procesamiento despues de aplicar los 3 fixes:
   #1 Cosecha_SAP: KgNeto -> Kg_Total_Raw (bronce/cargador.py)
   #2 Censo_Plantas: Linea_Raw -> cama en resolver geografia
   #3 Ciclo_Poda: hidratar Punto_Raw + dedupe con Valvula/Turno

 Pasos:
   PASO 1. Reparar Bronce.Cosecha_SAP (extraer KgNeto desde Valores_Raw).
   PASO 2. Limpiar cuarentena de los 3 origenes para que se vuelva a evaluar.
   PASO 3. Vaciar las 3 Facts Silver (forzar full reload).
   PASO 4. (Opcional) Refrescar los Marts Gold afectados.

 Despues de este script: correr 'python ETL\pipeline.py' (o el comando que
 use el equipo) para regenerar Silver -> Gold con la logica corregida.

 IDEMPOTENTE: se puede correr varias veces. Cada UPDATE/DELETE usa filtros
 que solo aplican si hay algo que reparar.

 NO HACE BACKUP. Hacer snapshot/backup de la BD antes de correr este script
 si los datos son productivos.
 ============================================================================
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRANSACTION;

-- ============================================================================
-- PASO 1: Reparar Bronce.Cosecha_SAP
-- ----------------------------------------------------------------------------
-- Antes del fix #1, el cargador escribia el kg neto como string dentro de
-- Valores_Raw ('... | KgNeto_Raw=14.2 | ...') en lugar de Kg_Total_Raw.
-- Aqui rescatamos el valor para los 315k registros ya ingeridos.
-- ============================================================================

PRINT '== PASO 1: Reparar Bronce.Cosecha_SAP (KgNeto -> Kg_Total_Raw) ==';

DECLARE @filas_reparadas INT = 0;

;WITH a_reparar AS (
    SELECT
        ID_Cosecha_SAP,
        Valores_Raw,
        CHARINDEX('KgNeto_Raw=', Valores_Raw) AS pos_ini
    FROM Bronce.Cosecha_SAP
    WHERE Kg_Total_Raw IS NULL
      AND Valores_Raw LIKE '%KgNeto_Raw=%'
), extraido AS (
    SELECT
        ID_Cosecha_SAP,
        Valores_Raw,
        pos_ini,
        -- inicio del valor numerico (despues de 'KgNeto_Raw=')
        pos_ini + LEN('KgNeto_Raw=') AS pos_valor,
        -- siguiente delimitador ' | ' DESPUES del valor (0 si es el ultimo token)
        NULLIF(CHARINDEX(' | ', Valores_Raw, pos_ini + LEN('KgNeto_Raw=')), 0) AS pos_fin
    FROM a_reparar
)
UPDATE b
SET b.Kg_Total_Raw = LTRIM(RTRIM(
        SUBSTRING(
            e.Valores_Raw,
            e.pos_valor,
            COALESCE(e.pos_fin, LEN(e.Valores_Raw) + 1) - e.pos_valor
        )
    ))
FROM Bronce.Cosecha_SAP b
JOIN extraido e ON e.ID_Cosecha_SAP = b.ID_Cosecha_SAP;

SET @filas_reparadas = @@ROWCOUNT;
PRINT CONCAT('  Filas con Kg_Total_Raw reparado: ', @filas_reparadas);

-- Validacion: cuantas siguen sin kg (deberian ser muy pocas o 0).
DECLARE @sin_kg INT = (
    SELECT COUNT(*) FROM Bronce.Cosecha_SAP
    WHERE Kg_Total_Raw IS NULL
);
PRINT CONCAT('  Filas que SIGUEN sin Kg_Total_Raw (revisar): ', @sin_kg);

-- Opcional: limpiar 'KgNeto_Raw=...' del Valores_Raw para no duplicar info.
-- Comentado por defecto; descomentar si quieres dejar Valores_Raw "limpio".
/*
UPDATE Bronce.Cosecha_SAP
SET Valores_Raw =
    LTRIM(RTRIM(
        REPLACE(
            REPLACE(Valores_Raw, CONCAT('KgNeto_Raw=', Kg_Total_Raw, ' | '), ''),
            CONCAT(' | KgNeto_Raw=', Kg_Total_Raw),
            ''
        )
    ))
WHERE Kg_Total_Raw IS NOT NULL
  AND Valores_Raw LIKE '%KgNeto_Raw=%';
*/


-- ============================================================================
-- PASO 2: Limpiar cuarentena de los 3 origenes
-- ----------------------------------------------------------------------------
-- Los registros que estaban en cuarentena por bugs ahora pueden re-evaluarse.
-- Solo borramos cuarentena en estado PENDIENTE (no aprobada/rechazada).
-- ============================================================================

PRINT '== PASO 2: Limpiar cuarentena pendiente de los 3 origenes ==';

DECLARE @cuar_borradas INT = 0;

DELETE FROM MDM.Cuarentena
WHERE Estado = 'PENDIENTE'
  AND Tabla_Origen IN (
      'Bronce.Cosecha_SAP',
      'Bronce.Censo_Plantas',
      'Bronce.Evaluacion_Calidad_Poda'
  );

SET @cuar_borradas = @@ROWCOUNT;
PRINT CONCAT('  Cuarentena pendiente borrada: ', @cuar_borradas);


-- ============================================================================
-- PASO 3: Vaciar Facts Silver para forzar full reload
-- ----------------------------------------------------------------------------
-- El cursor delta del pipeline (basado en Silver existente) hace que las
-- ultimas corridas vean 'Filas_Leidas=0'. Con TRUNCATE todo vuelve a 0 y se
-- vuelve a procesar Bronce completo con la logica nueva.
--
-- Si las Facts tienen FKs apuntando hacia ellas (Marts u otras Facts),
-- TRUNCATE puede fallar. En ese caso, sustituir por DELETE.
-- ============================================================================

PRINT '== PASO 3: Vaciar Silver.Fact_Cosecha_SAP, Fact_Censo_Plantas, Fact_Ciclo_Poda ==';

-- Cosecha_SAP: como Mart_Cosecha y Mart_Proyecciones la referencian, usar DELETE.
DELETE FROM Gold.Mart_Cosecha;
PRINT CONCAT('  Gold.Mart_Cosecha vaciado: ', @@ROWCOUNT, ' filas');

DELETE FROM Silver.Fact_Cosecha_SAP;
PRINT CONCAT('  Silver.Fact_Cosecha_SAP vaciado: ', @@ROWCOUNT, ' filas');

DELETE FROM Silver.Fact_Censo_Plantas;
PRINT CONCAT('  Silver.Fact_Censo_Plantas vaciado: ', @@ROWCOUNT, ' filas');

DELETE FROM Gold.Mart_Ciclo_Poda;
PRINT CONCAT('  Gold.Mart_Ciclo_Poda vaciado: ', @@ROWCOUNT, ' filas');

DELETE FROM Silver.Fact_Ciclo_Poda;
PRINT CONCAT('  Silver.Fact_Ciclo_Poda vaciado: ', @@ROWCOUNT, ' filas');


-- ============================================================================
-- PASO 4: Validacion previa al reproceso
-- ----------------------------------------------------------------------------
-- Conteos esperados despues del UPDATE de Paso 1 y antes de re-correr ETL.
-- ============================================================================

PRINT '== PASO 4: Snapshot pre-reproceso ==';

SELECT 'Bronce.Cosecha_SAP con Kg_Total_Raw' AS metrica,
       COUNT(*) AS valor
FROM Bronce.Cosecha_SAP
WHERE Kg_Total_Raw IS NOT NULL
UNION ALL
SELECT 'Bronce.Cosecha_SAP sin Kg_Total_Raw',
       COUNT(*) FROM Bronce.Cosecha_SAP WHERE Kg_Total_Raw IS NULL
UNION ALL
SELECT 'Bronce.Censo_Plantas con Linea_Raw',
       COUNT(*) FROM Bronce.Censo_Plantas WHERE Linea_Raw IS NOT NULL
UNION ALL
SELECT 'Bronce.Censo_Plantas sin Linea_Raw',
       COUNT(*) FROM Bronce.Censo_Plantas WHERE Linea_Raw IS NULL
UNION ALL
SELECT 'Bronce.Evaluacion_Calidad_Poda con Punto en Valores_Raw',
       COUNT(*) FROM Bronce.Evaluacion_Calidad_Poda WHERE Valores_Raw LIKE '%Punto_Raw=%'
UNION ALL
SELECT 'Silver.Fact_Cosecha_SAP (debe ser 0)', COUNT(*) FROM Silver.Fact_Cosecha_SAP
UNION ALL
SELECT 'Silver.Fact_Censo_Plantas (debe ser 0)', COUNT(*) FROM Silver.Fact_Censo_Plantas
UNION ALL
SELECT 'Silver.Fact_Ciclo_Poda (debe ser 0)', COUNT(*) FROM Silver.Fact_Ciclo_Poda
UNION ALL
SELECT 'MDM.Cuarentena PENDIENTE remanente',
       COUNT(*) FROM MDM.Cuarentena WHERE Estado='PENDIENTE';

COMMIT TRANSACTION;

PRINT '== Script completado. Siguiente paso: ejecutar el pipeline ETL para reprocesar Silver y Gold. ==';
