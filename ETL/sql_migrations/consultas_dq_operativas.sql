-- =============================================================================
-- consultas_dq_operativas.sql
-- =============================================================================
-- Consultas operativas para revisar backlog DQ y cuarentena.
-- Ejecutar en ACP_DataWarehose_Proyecciones.
-- =============================================================================

USE ACP_DataWarehose_Proyecciones;
GO

-- 1. Resumen diario de pendientes por tabla/campo/motivo
SELECT
    CAST(Fecha_Ingreso AS date) AS Fecha_DQ,
    Tabla_Origen,
    Campo_Origen,
    Motivo,
    COUNT(*) AS Filas_Pendientes
FROM MDM.Cuarentena
WHERE Estado = 'PENDIENTE'
GROUP BY
    CAST(Fecha_Ingreso AS date),
    Tabla_Origen,
    Campo_Origen,
    Motivo
ORDER BY Fecha_DQ DESC, Filas_Pendientes DESC;
GO

-- 2. Top motivos pendientes por tabla
SELECT
    Tabla_Origen,
    Motivo,
    COUNT(*) AS Filas_Pendientes
FROM MDM.Cuarentena
WHERE Estado = 'PENDIENTE'
GROUP BY Tabla_Origen, Motivo
ORDER BY Tabla_Origen, Filas_Pendientes DESC;
GO

-- 3. Valores crudos más repetidos pendientes
SELECT TOP (100)
    Tabla_Origen,
    Campo_Origen,
    Valor_Recibido,
    Motivo,
    COUNT(*) AS Veces
FROM MDM.Cuarentena
WHERE Estado = 'PENDIENTE'
GROUP BY Tabla_Origen, Campo_Origen, Valor_Recibido, Motivo
ORDER BY Veces DESC, Tabla_Origen, Campo_Origen;
GO

-- 4. Backlog focalizado para clima
SELECT
    Campo_Origen,
    Motivo,
    Valor_Recibido,
    COUNT(*) AS Veces
FROM MDM.Cuarentena
WHERE Estado = 'PENDIENTE'
  AND Tabla_Origen = 'Bronce.Clima'
GROUP BY Campo_Origen, Motivo, Valor_Recibido
ORDER BY Veces DESC, Campo_Origen, Motivo;
GO

-- 5. Últimos ingresos a cuarentena con trazabilidad de origen
SELECT TOP (200)
    ID_Cuarentena,
    Fecha_Ingreso,
    Tabla_Origen,
    Campo_Origen,
    Valor_Recibido,
    Motivo,
    Tipo_Regla,
    Estado,
    ID_Registro_Origen
FROM MDM.Cuarentena
ORDER BY Fecha_Ingreso DESC, ID_Cuarentena DESC;
GO
