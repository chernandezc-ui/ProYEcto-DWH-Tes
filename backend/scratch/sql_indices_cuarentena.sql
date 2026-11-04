/*
 * Índices recomendados para acelerar las queries de MDM.Cuarentena.
 *
 * Ejecutar UNA sola vez en SQL Server. Es idempotente — si los índices
 * ya existen no hace nada (los CREATE INDEX usan IF NOT EXISTS via
 * sys.indexes para compatibilidad con SQL Server 2012+).
 *
 * Impacto medido en queries del portal:
 *   - listar_pendientes:        full scan  → seek por (Estado, Fecha_Ingreso)
 *   - obtener_resumen / contar: hash agg   → stream agg sobre el índice
 *   - marcar_resuelto/descartado: ya usa PK, no cambia.
 *
 * Costo en storage: ~40 bytes/fila adicionales por índice.
 */

-- 1. Índice principal para paginación de pendientes ordenada por fecha desc.
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_Cuarentena_Estado_FechaIngreso'
      AND object_id = OBJECT_ID('MDM.Cuarentena')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_Cuarentena_Estado_FechaIngreso
        ON MDM.Cuarentena (Estado ASC, Fecha_Ingreso DESC, ID_Cuarentena DESC)
        INCLUDE (Tabla_Origen, Campo_Origen, Valor_Recibido, Motivo, ID_Registro_Origen)
        WITH (ONLINE = OFF, FILLFACTOR = 90);
    PRINT 'IX_Cuarentena_Estado_FechaIngreso creado.';
END
ELSE
    PRINT 'IX_Cuarentena_Estado_FechaIngreso ya existe.';

-- 2. Índice para el LIKE sobre Tabla_Origen cuando se usa filtro.
--    Sólo se justifica si la tabla supera ~100k filas pendientes.
--    Comentado por defecto; descomentar si la query de listar con filtro va lenta.
/*
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_Cuarentena_TablaOrigen'
      AND object_id = OBJECT_ID('MDM.Cuarentena')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_Cuarentena_TablaOrigen
        ON MDM.Cuarentena (Tabla_Origen)
        WHERE Estado = 'PENDIENTE';
END
*/

-- 3. Actualizar estadísticas tras crear índices.
UPDATE STATISTICS MDM.Cuarentena WITH FULLSCAN;
PRINT 'Estadísticas de MDM.Cuarentena actualizadas.';
