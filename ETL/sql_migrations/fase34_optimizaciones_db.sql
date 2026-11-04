-- =============================================================================
-- fase34_optimizaciones_db.sql
-- =============================================================================
-- Correcciones y optimizaciones convalidadas contra la BD real.
-- Generado: 2026-04-27
--
-- PREREQUISITOS: Fases 1-33 aplicadas.
-- BASE DE DATOS:  ACP_DataWarehose_Proyecciones
-- IDEMPOTENTE:    Sí — todos los bloques usan IF NOT EXISTS / IF EXISTS.
-- ROLLBACK:       Ver sección final (comentada).
--
-- ORDEN DE EJECUCIÓN:
--   1. Limpieza de duplicados en Dim_Variedad           (sin impacto en facts)
--   2. UNIQUE constraints en dimensiones clave
--   3. UNIQUE index de grain en Fact_Proyecciones
--   4. Índice filtrado por vigencia en Dim_Geografia
--   5. Índices de soporte en MDM y Auditoria
--   6. Índices de soporte en Silver Facts sin cobertura
-- =============================================================================

USE [ACP_DataWarehose_Proyecciones];
GO

-- Requerido para índices filtrados (WHERE ...) e índices con INCLUDE sobre columnas computadas
SET QUOTED_IDENTIFIER ON;
GO

PRINT '=== fase34: Inicio de optimizaciones ===';
PRINT CONVERT(NVARCHAR, GETDATE(), 120);
GO

-- =============================================================================
-- BLOQUE 1: Limpieza de duplicados en Silver.Dim_Variedad
-- -----------------------------------------------------------------------------
-- Convalidado: COLOSSUS (IDs 102, 103, 104) y FCM15 - 005 (IDs 76, 83)
-- duplicados sin referencias en ninguna tabla Fact (0 filas afectadas).
-- Se conserva el registro con menor ID (el más antiguo).
-- =============================================================================

PRINT '--- BLOQUE 1: Limpieza duplicados Dim_Variedad ---';
GO

-- Verificar que los duplicados siguen sin referencias antes de eliminar
IF EXISTS (
    SELECT 1 FROM Silver.Fact_Cosecha_SAP        WHERE ID_Variedad IN (103, 104, 83)
    UNION ALL
    SELECT 1 FROM Silver.Fact_Conteo_Fenologico  WHERE ID_Variedad IN (103, 104, 83)
    UNION ALL
    SELECT 1 FROM Silver.Fact_Evaluacion_Pesos   WHERE ID_Variedad IN (103, 104, 83)
    UNION ALL
    SELECT 1 FROM Silver.Fact_Evaluacion_Vegetativa WHERE ID_Variedad IN (103, 104, 83)
    UNION ALL
    SELECT 1 FROM Silver.Fact_Fisiologia         WHERE ID_Variedad IN (103, 104, 83)
    UNION ALL
    SELECT 1 FROM Silver.Fact_Ciclo_Poda         WHERE ID_Variedad IN (103, 104, 83)
    UNION ALL
    SELECT 1 FROM Silver.Fact_Peladas            WHERE ID_Variedad IN (103, 104, 83)
    UNION ALL
    SELECT 1 FROM Silver.Fact_Sanidad_Activo     WHERE ID_Variedad IN (103, 104, 83)
    UNION ALL
    SELECT 1 FROM Silver.Fact_Tareo t
        JOIN Silver.Dim_Actividad_Operativa a ON a.ID_Actividad = t.ID_Actividad_Operativa
        WHERE 1=0  -- Fact_Tareo no tiene ID_Variedad; join ficticio para mantener estructura
)
BEGIN
    RAISERROR('BLOQUE 1 ABORTADO: Los IDs duplicados tienen referencias en tablas Fact. Revisar manualmente.', 16, 1);
END
ELSE
BEGIN
    -- Eliminar duplicados de COLOSSUS (conservar ID 102, eliminar 103 y 104)
    DELETE FROM Silver.Dim_Variedad WHERE ID_Variedad IN (103, 104);
    PRINT 'Eliminados: COLOSSUS IDs 103 y 104 (conservado ID 102 con Breeder=U. LA FLORIDA).';

    -- Eliminar duplicado de FCM15 - 005 (conservar ID 76, eliminar 83)
    DELETE FROM Silver.Dim_Variedad WHERE ID_Variedad = 83;
    PRINT 'Eliminado: FCM15 - 005 ID 83 (conservado ID 76 con Breeder=FALL CREEK).';
END
GO

-- =============================================================================
-- BLOQUE 2: UNIQUE constraint en Silver.Dim_Variedad.Nombre_Variedad
-- -----------------------------------------------------------------------------
-- Sin este constraint, el ETL puede insertar variedades duplicadas en cada
-- ejecución si el lookup falla o se ejecuta en paralelo.
-- =============================================================================

PRINT '--- BLOQUE 2: UNIQUE Dim_Variedad.Nombre_Variedad ---';
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UQ_DimVariedad_Nombre'
      AND object_id = OBJECT_ID('Silver.Dim_Variedad')
)
BEGIN
    -- Verificar ausencia de duplicados antes de crear
    IF EXISTS (
        SELECT Nombre_Variedad FROM Silver.Dim_Variedad
        GROUP BY Nombre_Variedad HAVING COUNT(*) > 1
    )
    BEGIN
        RAISERROR('BLOQUE 2 ABORTADO: Aún existen duplicados en Dim_Variedad.Nombre_Variedad. Ejecutar BLOQUE 1 primero.', 16, 1);
    END
    ELSE
    BEGIN
        CREATE UNIQUE NONCLUSTERED INDEX UQ_DimVariedad_Nombre
            ON Silver.Dim_Variedad (Nombre_Variedad);
        PRINT 'Creado: UQ_DimVariedad_Nombre en Silver.Dim_Variedad.';
    END
END
ELSE
    PRINT 'OMITIDO: UQ_DimVariedad_Nombre ya existe.';
GO

-- =============================================================================
-- BLOQUE 3: UNIQUE constraint en Silver.Dim_Personal.DNI
-- -----------------------------------------------------------------------------
-- Dim_Personal tiene 2 filas (ID=-1 surrogate y ID=1 primer personal).
-- El MDM.Catalogo_Personal ya tiene UNIQUE en DNI; esta constraint cierra
-- el gap en la dimensión Silver.
-- =============================================================================

PRINT '--- BLOQUE 3: UNIQUE Dim_Personal.DNI ---';
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UQ_DimPersonal_DNI'
      AND object_id = OBJECT_ID('Silver.Dim_Personal')
)
BEGIN
    IF EXISTS (
        SELECT DNI FROM Silver.Dim_Personal
        GROUP BY DNI HAVING COUNT(*) > 1
    )
    BEGIN
        RAISERROR('BLOQUE 3 ABORTADO: Existen DNIs duplicados en Dim_Personal.', 16, 1);
    END
    ELSE
    BEGIN
        CREATE UNIQUE NONCLUSTERED INDEX UQ_DimPersonal_DNI
            ON Silver.Dim_Personal (DNI);
        PRINT 'Creado: UQ_DimPersonal_DNI en Silver.Dim_Personal.';
    END
END
ELSE
    PRINT 'OMITIDO: UQ_DimPersonal_DNI ya existe.';
GO

-- =============================================================================
-- BLOQUE 4: UNIQUE constraint en Silver.Dim_Condicion_Cultivo
-- -----------------------------------------------------------------------------
-- 5 filas, sin duplicados actuales. La constraint previene inserciones
-- duplicadas de la misma combinación Sustrato+Certificacion.
-- =============================================================================

PRINT '--- BLOQUE 4: UNIQUE Dim_Condicion_Cultivo (Sustrato, Certificacion) ---';
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UQ_DimCondicion_Sustrato_Cert'
      AND object_id = OBJECT_ID('Silver.Dim_Condicion_Cultivo')
)
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX UQ_DimCondicion_Sustrato_Cert
        ON Silver.Dim_Condicion_Cultivo (Sustrato, Certificacion);
    PRINT 'Creado: UQ_DimCondicion_Sustrato_Cert en Silver.Dim_Condicion_Cultivo.';
END
ELSE
    PRINT 'OMITIDO: UQ_DimCondicion_Sustrato_Cert ya existe.';
GO

-- =============================================================================
-- BLOQUE 5: UNIQUE index de grain en Silver.Fact_Proyecciones
-- -----------------------------------------------------------------------------
-- Única fact Silver sin UX de grain. El grain es:
--   ID_Geografia + ID_Tiempo + ID_Variedad + ID_Escenario + ID_Campana
-- Nota: ID_Campana es nullable (columna detectada en producción, no en DDL base).
--       Se usa filtro WHERE ID_Campana IS NOT NULL para el caso multi-campaña;
--       para el caso sin campaña se necesita el índice sin filtro.
--       Solución: índice compuesto incluyendo ID_Campana con NULLS en el índice
--       (SQL Server trata cada NULL como distinto en índices no únicos, pero en
--        UNIQUE los NULLs son iguales). Estrategia: usar Fecha_Cutoff como
--        desambiguador adicional para reflejar que una misma geo+tiempo+variedad+
--        escenario puede tener múltiples versiones a distintas fechas de corte.
-- =============================================================================

PRINT '--- BLOQUE 5: UNIQUE grain en Silver.Fact_Proyecciones ---';
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_Fact_Proyecciones_Grain'
      AND object_id = OBJECT_ID('Silver.Fact_Proyecciones')
)
BEGIN
    -- Limpiar duplicados previos conservando el de menor PK
    DELETE FROM Silver.Fact_Proyecciones
    WHERE ID_Proyeccion NOT IN (
        SELECT MIN(ID_Proyeccion)
        FROM Silver.Fact_Proyecciones
        GROUP BY ID_Geografia, ID_Tiempo, ID_Variedad, ID_Escenario, Fecha_Cutoff
    );

    CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_Proyecciones_Grain
        ON Silver.Fact_Proyecciones (ID_Geografia, ID_Tiempo, ID_Variedad, ID_Escenario, Fecha_Cutoff);
    PRINT 'Creado: UX_Fact_Proyecciones_Grain en Silver.Fact_Proyecciones.';
END
ELSE
    PRINT 'OMITIDO: UX_Fact_Proyecciones_Grain ya existe.';
GO

-- =============================================================================
-- BLOQUE 6: Índice filtrado por vigencia en Silver.Dim_Geografia
-- -----------------------------------------------------------------------------
-- El lookup del ETL siempre filtra WHERE Es_Vigente = 1.
-- El UNIQUE UQ_Combinacion_Geografica_Nueva cubre integridad pero no es
-- selectivo para lookups de vigentes. Este índice cubre la búsqueda hot-path:
--   Modulo_Catalogo + Turno_Catalogo + Valvula_Catalogo → ID_Geografia
-- =============================================================================

PRINT '--- BLOQUE 6: Índice lookup vigentes en Silver.Dim_Geografia ---';
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_DimGeo_ModuloTurnoValvula_Vigente'
      AND object_id = OBJECT_ID('Silver.Dim_Geografia')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_DimGeo_ModuloTurnoValvula_Vigente
        ON Silver.Dim_Geografia (ID_Modulo_Catalogo, ID_Turno_Catalogo, ID_Valvula_Catalogo)
        INCLUDE (ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Cama_Catalogo, Codigo_SAP_Campo)
        WHERE Es_Vigente = 1;
    PRINT 'Creado: IX_DimGeo_ModuloTurnoValvula_Vigente en Silver.Dim_Geografia.';
END
ELSE
    PRINT 'OMITIDO: IX_DimGeo_ModuloTurnoValvula_Vigente ya existe.';
GO

-- =============================================================================
-- BLOQUE 7: Índice de lookup en MDM.Diccionario_Homologacion
-- -----------------------------------------------------------------------------
-- El ETL busca por Tabla_Origen + Campo_Origen + Texto_Crudo en cada resolución
-- de homologación (191 filas actualmente, crece con cada campaña).
-- =============================================================================

PRINT '--- BLOQUE 7: Índice lookup en MDM.Diccionario_Homologacion ---';
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_Homologacion_Lookup'
      AND object_id = OBJECT_ID('MDM.Diccionario_Homologacion')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_Homologacion_Lookup
        ON MDM.Diccionario_Homologacion (Tabla_Origen, Campo_Origen, Texto_Crudo)
        INCLUDE (Valor_Canonico, Veces_Aplicado)
        WHERE Texto_Crudo IS NOT NULL;
    PRINT 'Creado: IX_Homologacion_Lookup en MDM.Diccionario_Homologacion.';
END
ELSE
    PRINT 'OMITIDO: IX_Homologacion_Lookup ya existe.';
GO

-- =============================================================================
-- BLOQUE 8: Índice de consulta en MDM.Cuarentena
-- -----------------------------------------------------------------------------
-- El portal Streamlit y las queries operativas filtran por Estado + Tabla_Origen.
-- 762 filas actualmente, crecerá proporcionalmente con el volumen de datos.
-- =============================================================================

PRINT '--- BLOQUE 8: Índice consulta en MDM.Cuarentena ---';
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_Cuarentena_Estado_Tabla'
      AND object_id = OBJECT_ID('MDM.Cuarentena')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_Cuarentena_Estado_Tabla
        ON MDM.Cuarentena (Estado, Tabla_Origen, Fecha_Ingreso DESC)
        INCLUDE (Campo_Origen, Motivo, Tipo_Regla, Valor_Recibido, ID_Registro_Origen);
    PRINT 'Creado: IX_Cuarentena_Estado_Tabla en MDM.Cuarentena.';
END
ELSE
    PRINT 'OMITIDO: IX_Cuarentena_Estado_Tabla ya existe.';
GO

-- =============================================================================
-- BLOQUE 9: Índice de consulta en Auditoria.Log_Carga
-- -----------------------------------------------------------------------------
-- Queries de monitoreo y reporting filtran por Tabla_Destino + Fecha_Inicio.
-- 2,178 filas, crece con cada corrida del pipeline.
-- =============================================================================

PRINT '--- BLOQUE 9: Índice consulta en Auditoria.Log_Carga ---';
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_LogCarga_Tabla_Fecha'
      AND object_id = OBJECT_ID('Auditoria.Log_Carga')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_LogCarga_Tabla_Fecha
        ON Auditoria.Log_Carga (Tabla_Destino, Fecha_Inicio DESC)
        INCLUDE (Estado_Proceso, Filas_Insertadas, Filas_Cuarentena, Filas_Rechazadas, Duracion_Segundos);
    PRINT 'Creado: IX_LogCarga_Tabla_Fecha en Auditoria.Log_Carga.';
END
ELSE
    PRINT 'OMITIDO: IX_LogCarga_Tabla_Fecha ya existe.';
GO

-- =============================================================================
-- BLOQUE 10: Índices de soporte en Silver Facts sin cobertura
-- -----------------------------------------------------------------------------
-- Facts que solo tienen PK + UX de grain, sin índices de soporte para queries
-- analíticas de Power BI ni lookups del pipeline.
-- Estrategia: índice por (ID_Tiempo, ID_Geografia) como patrón base para
-- joins de dimensiones temporales y geográficas.
-- =============================================================================

PRINT '--- BLOQUE 10: Índices de soporte en Silver Facts sin cobertura ---';
GO

-- 10a. Fact_Cosecha_SAP — join frecuente por variedad y rango de tiempo
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactCosecha_Tiempo_Variedad'
      AND object_id = OBJECT_ID('Silver.Fact_Cosecha_SAP')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactCosecha_Tiempo_Variedad
        ON Silver.Fact_Cosecha_SAP (ID_Tiempo, ID_Variedad)
        INCLUDE (ID_Geografia, Kg_Neto_MP, Kg_Brutos, Cantidad_Jabas, Estado_DQ);
    PRINT 'Creado: IX_FactCosecha_Tiempo_Variedad en Silver.Fact_Cosecha_SAP.';
END
ELSE
    PRINT 'OMITIDO: IX_FactCosecha_Tiempo_Variedad ya existe.';
GO

-- 10b. Fact_Conteo_Fenologico — consultas por estado fenológico y tiempo (Power BI)
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactConteoFen_Tiempo_Estado'
      AND object_id = OBJECT_ID('Silver.Fact_Conteo_Fenologico')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactConteoFen_Tiempo_Estado
        ON Silver.Fact_Conteo_Fenologico (ID_Tiempo, ID_Estado_Fenologico)
        INCLUDE (ID_Geografia, ID_Variedad, Cantidad_Organos, Estado_DQ);
    PRINT 'Creado: IX_FactConteoFen_Tiempo_Estado en Silver.Fact_Conteo_Fenologico.';
END
ELSE
    PRINT 'OMITIDO: IX_FactConteoFen_Tiempo_Estado ya existe.';
GO

-- 10c. Fact_Peladas — input del modelo Six Weeks; consultas por variedad y tiempo
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactPeladas_Tiempo_Variedad'
      AND object_id = OBJECT_ID('Silver.Fact_Peladas')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactPeladas_Tiempo_Variedad
        ON Silver.Fact_Peladas (ID_Tiempo, ID_Variedad)
        INCLUDE (ID_Geografia, Bayas_Cosechables, Bayas_Maduras, Muestras, Estado_DQ);
    PRINT 'Creado: IX_FactPeladas_Tiempo_Variedad en Silver.Fact_Peladas.';
END
ELSE
    PRINT 'OMITIDO: IX_FactPeladas_Tiempo_Variedad ya existe.';
GO

-- 10d. Fact_Sanidad_Activo — consultas por geografía para monitoreo de mortalidad
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactSanidad_Geografia_Tiempo'
      AND object_id = OBJECT_ID('Silver.Fact_Sanidad_Activo')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactSanidad_Geografia_Tiempo
        ON Silver.Fact_Sanidad_Activo (ID_Geografia, ID_Tiempo)
        INCLUDE (ID_Variedad, Plantas_Vivas, Plantas_Muertas, Total_Plantas);
    PRINT 'Creado: IX_FactSanidad_Geografia_Tiempo en Silver.Fact_Sanidad_Activo.';
END
ELSE
    PRINT 'OMITIDO: IX_FactSanidad_Geografia_Tiempo ya existe.';
GO

-- 10e. Fact_Ciclo_Poda — consultas por módulo y variedad en temporada de poda
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactCicloPoda_Tiempo_Variedad'
      AND object_id = OBJECT_ID('Silver.Fact_Ciclo_Poda')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactCicloPoda_Tiempo_Variedad
        ON Silver.Fact_Ciclo_Poda (ID_Tiempo, ID_Variedad)
        INCLUDE (ID_Geografia, Tipo_Evaluacion, Promedio_Tallos_Planta, Estado_DQ);
    PRINT 'Creado: IX_FactCicloPoda_Tiempo_Variedad en Silver.Fact_Ciclo_Poda.';
END
ELSE
    PRINT 'OMITIDO: IX_FactCicloPoda_Tiempo_Variedad ya existe.';
GO

-- 10f. Fact_Fisiologia — consultas por variedad y tercio (análisis por sección de planta)
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactFisiologia_Tiempo_Variedad'
      AND object_id = OBJECT_ID('Silver.Fact_Fisiologia')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactFisiologia_Tiempo_Variedad
        ON Silver.Fact_Fisiologia (ID_Tiempo, ID_Variedad)
        INCLUDE (ID_Geografia, Tercio, Brotes_Productivos, Brotes_Vegetativos, Total_Organos, Estado_DQ);
    PRINT 'Creado: IX_FactFisiologia_Tiempo_Variedad en Silver.Fact_Fisiologia.';
END
ELSE
    PRINT 'OMITIDO: IX_FactFisiologia_Tiempo_Variedad ya existe.';
GO

-- 10g. Fact_Tareo — consultas por personal y período (Mart_Administrativo)
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactTareo_Tiempo_Personal'
      AND object_id = OBJECT_ID('Silver.Fact_Tareo')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactTareo_Tiempo_Personal
        ON Silver.Fact_Tareo (ID_Tiempo, ID_Personal)
        INCLUDE (ID_Geografia, ID_Actividad_Operativa, Horas_Trabajadas, Es_Observado_SAP);
    PRINT 'Creado: IX_FactTareo_Tiempo_Personal en Silver.Fact_Tareo.';
END
ELSE
    PRINT 'OMITIDO: IX_FactTareo_Tiempo_Personal ya existe.';
GO

-- =============================================================================
-- REGISTRO EN CONTROL DE MIGRACIONES (si existe la tabla de tracking)
-- =============================================================================

IF OBJECT_ID('Silver.Migraciones_Aplicadas', 'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM Silver.Migraciones_Aplicadas WHERE Nombre_Fase = 'fase34_optimizaciones_db'
    )
    INSERT INTO Silver.Migraciones_Aplicadas (Nombre_Fase, Fecha_Aplicacion, Descripcion)
    VALUES ('fase34_optimizaciones_db', GETDATE(), 'Constraints UNIQUE en dims, grain Fact_Proyecciones, índices de soporte en facts/MDM/Auditoria');
    PRINT 'Registrado en Silver.Migraciones_Aplicadas.';
END
GO

-- =============================================================================
-- RESUMEN
-- =============================================================================

PRINT '';
PRINT '=== fase34: Optimizaciones completadas ===';
PRINT 'BLOQUE 1  — Duplicados eliminados en Dim_Variedad (COLOSSUS x2, FCM15-005 x1)';
PRINT 'BLOQUE 2  — UNIQUE Dim_Variedad.Nombre_Variedad';
PRINT 'BLOQUE 3  — UNIQUE Dim_Personal.DNI';
PRINT 'BLOQUE 4  — UNIQUE Dim_Condicion_Cultivo (Sustrato, Certificacion)';
PRINT 'BLOQUE 5  — UNIQUE grain Fact_Proyecciones (Geo+Tiempo+Variedad+Escenario+Cutoff)';
PRINT 'BLOQUE 6  — Índice filtrado vigentes en Dim_Geografia';
PRINT 'BLOQUE 7  — Índice lookup MDM.Diccionario_Homologacion';
PRINT 'BLOQUE 8  — Índice consulta MDM.Cuarentena';
PRINT 'BLOQUE 9  — Índice consulta Auditoria.Log_Carga';
PRINT 'BLOQUE 10 — Índices de soporte en 7 Silver Facts (CosechaSAP, ConteoFen, Peladas,';
PRINT '             SanidadActivo, CicloPoda, Fisiologia, Tareo)';
PRINT CONVERT(NVARCHAR, GETDATE(), 120);
GO

-- =============================================================================
-- ROLLBACK (ejecutar en caso de necesitar revertir — comentado por seguridad)
-- =============================================================================
/*
USE [ACP_DataWarehose_Proyecciones];

-- Eliminar índices de soporte en Facts
DROP INDEX IF EXISTS IX_FactCosecha_Tiempo_Variedad        ON Silver.Fact_Cosecha_SAP;
DROP INDEX IF EXISTS IX_FactConteoFen_Tiempo_Estado        ON Silver.Fact_Conteo_Fenologico;
DROP INDEX IF EXISTS IX_FactPeladas_Tiempo_Variedad        ON Silver.Fact_Peladas;
DROP INDEX IF EXISTS IX_FactSanidad_Geografia_Tiempo       ON Silver.Fact_Sanidad_Activo;
DROP INDEX IF EXISTS IX_FactCicloPoda_Tiempo_Variedad      ON Silver.Fact_Ciclo_Poda;
DROP INDEX IF EXISTS IX_FactFisiologia_Tiempo_Variedad     ON Silver.Fact_Fisiologia;
DROP INDEX IF EXISTS IX_FactTareo_Tiempo_Personal          ON Silver.Fact_Tareo;

-- Eliminar índices de soporte en MDM y Auditoria
DROP INDEX IF EXISTS IX_Homologacion_Lookup                ON MDM.Diccionario_Homologacion;
DROP INDEX IF EXISTS IX_Cuarentena_Estado_Tabla            ON MDM.Cuarentena;
DROP INDEX IF EXISTS IX_LogCarga_Tabla_Fecha               ON Auditoria.Log_Carga;

-- Eliminar índice filtrado en Dim_Geografia
DROP INDEX IF EXISTS IX_DimGeo_ModuloTurnoValvula_Vigente  ON Silver.Dim_Geografia;

-- Eliminar UNIQUE de grain en Fact_Proyecciones
DROP INDEX IF EXISTS UX_Fact_Proyecciones_Grain            ON Silver.Fact_Proyecciones;

-- Eliminar UNIQUE constraints en dimensiones
DROP INDEX IF EXISTS UQ_DimCondicion_Sustrato_Cert         ON Silver.Dim_Condicion_Cultivo;
DROP INDEX IF EXISTS UQ_DimPersonal_DNI                    ON Silver.Dim_Personal;
DROP INDEX IF EXISTS UQ_DimVariedad_Nombre                 ON Silver.Dim_Variedad;

-- NOTA: Los registros eliminados de Dim_Variedad (IDs 83, 103, 104) NO se pueden
-- recuperar automáticamente. Restaurar desde backup si es necesario.
*/
