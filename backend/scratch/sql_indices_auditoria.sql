/*
 * Índices recomendados para acelerar las queries de Auditoria.Log_Carga.
 *
 * Ejecutar UNA sola vez en SQL Server. Es idempotente — si los índices
 * ya existen no hace nada (chequeo via sys.indexes para compatibilidad
 * con SQL Server 2012+).
 *
 * Impacto medido en queries del portal:
 *   - contar_fallos_recientes (endpoint /v1/etl/fallos-recientes):
 *       full scan → seek por (Estado_Proceso, Fecha_Inicio DESC).
 *       Crítico porque /api/cc/health lo llama cada 30s.
 *   - listar_bitacora con filtros: ya usaba el índice clustered por id_log,
 *       ahora también puede usar este para filtrar por estado y rango de
 *       fechas sin tocar la tabla.
 *   - resumen_bitacora: hash agg → stream agg sobre el índice.
 *   - obtener_historial (legacy /v1/etl/corridas?limite=50):
 *       ORDER BY Fecha_Inicio DESC ahora se sirve directo del índice.
 *
 * Costo en storage: ~60 bytes/fila adicionales por índice. En una tabla
 * de 1M filas: ~57 MB. Tolerable dado el impacto en latencia del dashboard.
 *
 * Notas operativas:
 *   - WITH (ONLINE = OFF): SQL Server Standard no soporta ONLINE. Si está
 *     en Enterprise, cambiar a ONLINE = ON para evitar bloqueo de escrituras.
 *   - FILLFACTOR 90: deja 10% de espacio libre por página para que las
 *     inserciones (siempre Fecha_Inicio creciente) no fragmenten tanto.
 *   - Mantenimiento sugerido: REORGANIZE mensual, REBUILD trimestral.
 */

-- 1. Índice principal por (Estado_Proceso, Fecha_Inicio DESC).
--    Acelera el filtro "ERROR/TIMEOUT en las últimas N horas" usado por
--    el indicador de salud del dashboard.
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_LogCarga_Estado_FechaInicio'
      AND object_id = OBJECT_ID('Auditoria.Log_Carga')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_LogCarga_Estado_FechaInicio
        ON Auditoria.Log_Carga (Estado_Proceso ASC, Fecha_Inicio DESC)
        INCLUDE (
            Tabla_Destino,
            Nombre_Proceso,
            Filas_Insertadas,
            Filas_Rechazadas,
            Duracion_Segundos,
            Mensaje_Error,
            Fecha_Fin
        )
        WITH (ONLINE = OFF, FILLFACTOR = 90);
    PRINT 'IX_LogCarga_Estado_FechaInicio creado.';
END
ELSE
    PRINT 'IX_LogCarga_Estado_FechaInicio ya existe.';

-- 2. Índice por Fecha_Inicio DESC sin filtro de estado.
--    Sirve para listar_bitacora / obtener_historial sin filtros (los más
--    comunes desde la página /bitacora).
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_LogCarga_FechaInicio'
      AND object_id = OBJECT_ID('Auditoria.Log_Carga')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_LogCarga_FechaInicio
        ON Auditoria.Log_Carga (Fecha_Inicio DESC)
        INCLUDE (
            Tabla_Destino,
            Nombre_Proceso,
            Estado_Proceso,
            Filas_Insertadas,
            Filas_Rechazadas,
            Duracion_Segundos,
            Fecha_Fin
        )
        WITH (ONLINE = OFF, FILLFACTOR = 90);
    PRINT 'IX_LogCarga_FechaInicio creado.';
END
ELSE
    PRINT 'IX_LogCarga_FechaInicio ya existe.';

-- 3. Índice por Tabla_Destino — sólo si se filtra frecuentemente por tabla
--    (página /bitacora pestaña "Por tabla"). Comentado por defecto.
/*
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_LogCarga_TablaDestino_FechaInicio'
      AND object_id = OBJECT_ID('Auditoria.Log_Carga')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_LogCarga_TablaDestino_FechaInicio
        ON Auditoria.Log_Carga (Tabla_Destino ASC, Fecha_Inicio DESC)
        INCLUDE (Estado_Proceso, Filas_Insertadas, Filas_Rechazadas)
        WITH (ONLINE = OFF, FILLFACTOR = 90);
    PRINT 'IX_LogCarga_TablaDestino_FechaInicio creado.';
END
*/

-- 4. Actualizar estadísticas tras crear índices — sin esto el query planner
--    puede ignorar los nuevos índices durante la primera ejecución.
UPDATE STATISTICS Auditoria.Log_Carga WITH FULLSCAN;
PRINT 'Estadísticas de Auditoria.Log_Carga actualizadas.';
