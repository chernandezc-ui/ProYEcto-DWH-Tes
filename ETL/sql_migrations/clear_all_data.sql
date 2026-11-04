-- =============================================================================
-- SCRIPT DE LIMPIEZA TOTAL: BRONCE, SILVER (FACTS/BRIDGES) Y GOLD (MARTS)
-- Base de Datos: ACP_DataWarehose_Proyecciones
-- 
-- Explicación sobre las vistas:
-- Las vistas (ej. Silver.vFact_Floracion, etc.) son objetos virtuales/consultas.
-- No almacenan datos físicamente. Al vaciar las tablas físicas de la capa Silver,
-- las vistas se vaciarán automáticamente. No es necesario (ni posible) truncarlas.
-- =============================================================================

USE ACP_DataWarehose_Proyecciones;
GO

PRINT '----------------------------------------------------------------------';
PRINT 'INICIANDO LIMPIEZA DE DATOS DWH...';
PRINT '----------------------------------------------------------------------';

-- =============================================================================
-- 1. LIMPIEZA DE CAPA GOLD (MARTS)
-- =============================================================================
PRINT 'Vaciando tablas de la capa GOLD (Marts)...';

IF OBJECT_ID('Gold.Mart_Cosecha', 'U') IS NOT NULL              TRUNCATE TABLE Gold.Mart_Cosecha;
IF OBJECT_ID('Gold.Mart_Proyecciones', 'U') IS NOT NULL         TRUNCATE TABLE Gold.Mart_Proyecciones;
IF OBJECT_ID('Gold.Mart_Fenologia', 'U') IS NOT NULL            TRUNCATE TABLE Gold.Mart_Fenologia;
IF OBJECT_ID('Gold.Mart_Clima', 'U') IS NOT NULL                TRUNCATE TABLE Gold.Mart_Clima;
IF OBJECT_ID('Gold.Mart_Pesos_Calibres', 'U') IS NOT NULL       TRUNCATE TABLE Gold.Mart_Pesos_Calibres;
IF OBJECT_ID('Gold.Mart_Administrativo', 'U') IS NOT NULL       TRUNCATE TABLE Gold.Mart_Administrativo;
IF OBJECT_ID('Gold.Mart_Fisiologia', 'U') IS NOT NULL           TRUNCATE TABLE Gold.Mart_Fisiologia;
IF OBJECT_ID('Gold.Mart_Evaluacion_Vegetativa', 'U') IS NOT NULL TRUNCATE TABLE Gold.Mart_Evaluacion_Vegetativa;
IF OBJECT_ID('Gold.Mart_Maduracion', 'U') IS NOT NULL           TRUNCATE TABLE Gold.Mart_Maduracion;
IF OBJECT_ID('Gold.Mart_Tasa_Crecimiento', 'U') IS NOT NULL     TRUNCATE TABLE Gold.Mart_Tasa_Crecimiento;
IF OBJECT_ID('Gold.Mart_Induccion_Floral', 'U') IS NOT NULL     TRUNCATE TABLE Gold.Mart_Induccion_Floral;
IF OBJECT_ID('Gold.Mart_Ciclo_Poda', 'U') IS NOT NULL           TRUNCATE TABLE Gold.Mart_Ciclo_Poda;
IF OBJECT_ID('Gold.Mart_Peladas', 'U') IS NOT NULL              TRUNCATE TABLE Gold.Mart_Peladas;

PRINT '✔ Capa GOLD (Marts) vaciada.';

-- =============================================================================
-- 2. LIMPIEZA DE CAPA SILVER (FACTS & BRIDGES)
-- Ninguna dimensión u otra tabla depende de las Facts/Bridges, por lo que 
-- se pueden vaciar directamente con TRUNCATE restableciendo los contadores IDENTITY.
-- =============================================================================
PRINT 'Vaciando tablas de hechos (Facts) y puentes (Bridges) de la capa SILVER...';

IF OBJECT_ID('Silver.Fact_Cosecha_SAP', 'U') IS NOT NULL           TRUNCATE TABLE Silver.Fact_Cosecha_SAP;
IF OBJECT_ID('Silver.Fact_Conteo_Fenologico', 'U') IS NOT NULL     TRUNCATE TABLE Silver.Fact_Conteo_Fenologico;
IF OBJECT_ID('Silver.Fact_Telemetria_Clima', 'U') IS NOT NULL      TRUNCATE TABLE Silver.Fact_Telemetria_Clima;
IF OBJECT_ID('Silver.Fact_Proyecciones', 'U') IS NOT NULL          TRUNCATE TABLE Silver.Fact_Proyecciones;
IF OBJECT_ID('Silver.Fact_Evaluacion_Vegetativa', 'U') IS NOT NULL TRUNCATE TABLE Silver.Fact_Evaluacion_Vegetativa;
IF OBJECT_ID('Silver.Fact_Floracion', 'U') IS NOT NULL             TRUNCATE TABLE Silver.Fact_Floracion;
IF OBJECT_ID('Silver.Fact_Sanidad_Activo', 'U') IS NOT NULL        TRUNCATE TABLE Silver.Fact_Sanidad_Activo;
IF OBJECT_ID('Silver.Fact_Evaluacion_Pesos', 'U') IS NOT NULL      TRUNCATE TABLE Silver.Fact_Evaluacion_Pesos;
IF OBJECT_ID('Silver.Fact_Ciclo_Poda', 'U') IS NOT NULL            TRUNCATE TABLE Silver.Fact_Ciclo_Poda;
IF OBJECT_ID('Silver.Fact_Tareo', 'U') IS NOT NULL                 TRUNCATE TABLE Silver.Fact_Tareo;
IF OBJECT_ID('Silver.Fact_Fisiologia', 'U') IS NOT NULL            TRUNCATE TABLE Silver.Fact_Fisiologia;
IF OBJECT_ID('Silver.Fact_Peladas', 'U') IS NOT NULL               TRUNCATE TABLE Silver.Fact_Peladas;
IF OBJECT_ID('Silver.Fact_Maduracion', 'U') IS NOT NULL            TRUNCATE TABLE Silver.Fact_Maduracion;
IF OBJECT_ID('Silver.Fact_Induccion_Floral', 'U') IS NOT NULL      TRUNCATE TABLE Silver.Fact_Induccion_Floral;
IF OBJECT_ID('Silver.Fact_Tasa_Crecimiento_Brotes', 'U') IS NOT NULL TRUNCATE TABLE Silver.Fact_Tasa_Crecimiento_Brotes;
IF OBJECT_ID('Silver.Fact_areas_plantas', 'U') IS NOT NULL         TRUNCATE TABLE Silver.Fact_areas_plantas;
IF OBJECT_ID('Silver.Fact_Censo_Plantas', 'U') IS NOT NULL         TRUNCATE TABLE Silver.Fact_Censo_Plantas;

-- Tablas puente (Bridges)
IF OBJECT_ID('Silver.Bridge_Geografia_Cama', 'U') IS NOT NULL      TRUNCATE TABLE Silver.Bridge_Geografia_Cama;

PRINT '✔ Capa SILVER (Facts y Bridges) vaciada.';

-- =============================================================================
-- 3. LIMPIEZA DE CAPA BRONCE (TABLAS DE INGESTA)
-- =============================================================================
PRINT 'Vaciando tablas de la capa BRONCE...';

IF OBJECT_ID('Bronce.Dashboard', 'U') IS NOT NULL               TRUNCATE TABLE Bronce.Dashboard;
IF OBJECT_ID('Bronce.Conteo_Fruta', 'U') IS NOT NULL            TRUNCATE TABLE Bronce.Conteo_Fruta;
IF OBJECT_ID('Bronce.Induccion_Floral', 'U') IS NOT NULL        TRUNCATE TABLE Bronce.Induccion_Floral;
IF OBJECT_ID('Bronce.Ciclos_Fenologicos', 'U') IS NOT NULL      TRUNCATE TABLE Bronce.Ciclos_Fenologicos;
IF OBJECT_ID('Bronce.Maduracion', 'U') IS NOT NULL              TRUNCATE TABLE Bronce.Maduracion;
IF OBJECT_ID('Bronce.Pintado_Flores', 'U') IS NOT NULL          TRUNCATE TABLE Bronce.Pintado_Flores;
IF OBJECT_ID('Bronce.Peladas', 'U') IS NOT NULL                 TRUNCATE TABLE Bronce.Peladas;
IF OBJECT_ID('Bronce.Evaluacion_Vegetativa', 'U') IS NOT NULL   TRUNCATE TABLE Bronce.Evaluacion_Vegetativa;
IF OBJECT_ID('Bronce.Tasa_Crecimiento_Brotes', 'U') IS NOT NULL TRUNCATE TABLE Bronce.Tasa_Crecimiento_Brotes;
IF OBJECT_ID('Bronce.Evaluacion_Calidad_Poda', 'U') IS NOT NULL TRUNCATE TABLE Bronce.Evaluacion_Calidad_Poda;
IF OBJECT_ID('Bronce.Fisiologia', 'U') IS NOT NULL              TRUNCATE TABLE Bronce.Fisiologia;
IF OBJECT_ID('Bronce.Calibres', 'U') IS NOT NULL                TRUNCATE TABLE Bronce.Calibres;
IF OBJECT_ID('Bronce.Consolidado_Tareos', 'U') IS NOT NULL      TRUNCATE TABLE Bronce.Consolidado_Tareos;
IF OBJECT_ID('Bronce.Fiscalizacion', 'U') IS NOT NULL           TRUNCATE TABLE Bronce.Fiscalizacion;
IF OBJECT_ID('Bronce.Seguimiento_Errores', 'U') IS NOT NULL     TRUNCATE TABLE Bronce.Seguimiento_Errores;
IF OBJECT_ID('Bronce.Evaluacion_Pesos', 'U') IS NOT NULL        TRUNCATE TABLE Bronce.Evaluacion_Pesos;
IF OBJECT_ID('Bronce.Reporte_Cosecha', 'U') IS NOT NULL         TRUNCATE TABLE Bronce.Reporte_Cosecha;
IF OBJECT_ID('Bronce.Cierre_Mapas_Cosecha', 'U') IS NOT NULL    TRUNCATE TABLE Bronce.Cierre_Mapas_Cosecha;
IF OBJECT_ID('Bronce.Reporte_Clima', 'U') IS NOT NULL           TRUNCATE TABLE Bronce.Reporte_Clima;
IF OBJECT_ID('Bronce.Variables_Meteorologicas', 'U') IS NOT NULL TRUNCATE TABLE Bronce.Variables_Meteorologicas;
IF OBJECT_ID('Bronce.Data_SAP', 'U') IS NOT NULL                TRUNCATE TABLE Bronce.Data_SAP;
IF OBJECT_ID('Bronce.Proyeccion_Pesos', 'U') IS NOT NULL        TRUNCATE TABLE Bronce.Proyeccion_Pesos;

PRINT '✔ Capa BRONCE vaciada.';

-- =============================================================================
-- [OPCIONAL] 4. LIMPIEZA DE AUDITORÍA Y CUARENTENA (MDM)
-- Descomenta las siguientes líneas si también deseas resetear las colas de rechazo/cuarentena
-- =============================================================================
-- PRINT 'Vaciando tablas del esquema MDM (Cuarentena y Auditoría)...';
-- IF OBJECT_ID('MDM.Cuarentena', 'U') IS NOT NULL               TRUNCATE TABLE MDM.Cuarentena;
-- IF OBJECT_ID('MDM.Log_Errores', 'U') IS NOT NULL              TRUNCATE TABLE MDM.Log_Errores;
-- PRINT '✔ Esquema MDM vaciado.';

PRINT '----------------------------------------------------------------------';
PRINT '¡LIMPIEZA COMPLETA DEL DWH EXITOSA!';
PRINT '----------------------------------------------------------------------';
GO
