-- ==============================================================================
-- FASE 48C: Vista Gold para PowerBI - Evaluación Vegetativa con Campaña
-- ==============================================================================
USE ACP_DataWarehose_Proyecciones;
GO

CREATE OR ALTER VIEW Gold.vw_Analitica_Evaluacion_Vegetativa_Campana AS
SELECT 
    -- 1. Hechos Base
    f.ID_Fact_Evaluacion_Vegetativa,
    f.Piso,
    f.Brotes_Generales,
    f.Brotes_Productivos,
    f.Diametro_Brote,
    f.Altura,
    f.Tallos_Basales,
    f.Tallos_Basales_Nuevos,
    f.Semanas_Despues_Poda,
    f.Fecha_Evento,
    
    -- 2. Dimensión Tiempo
    t.Fecha AS Tiempo_Fecha,
    t.Anio AS Tiempo_Anio,
    t.Mes AS Tiempo_Mes,
    t.Semana_ISO AS Tiempo_Semana,
    
    -- 3. Dimensión Variedad
    v.Nombre_Variedad,
    
    -- 4. Dimensión Geografía Expandida
    s.Sector,
    m.Modulo,
    tu.Turno,
    va.Valvula,
    ca.Cama_Normalizada AS Cama,
    
    -- 5. Dimensión Campaña (El "Slicer" mágico)
    c.Nombre_Campana,
    c.Anio_Cosecha AS Campana_Anio_Cosecha,
    c.Fecha_Inicio_Poda,
    c.Fecha_Fin_Campana,
    
    -- Flag de Bridge Activo
    bgc.Es_Activa AS Es_Geografia_Valida_En_Campana

FROM Silver.Fact_Evaluacion_Vegetativa f
INNER JOIN Silver.Dim_Tiempo t 
    ON f.ID_Tiempo = t.ID_Tiempo
INNER JOIN Silver.Dim_Variedad v 
    ON f.ID_Variedad = v.ID_Variedad
INNER JOIN Silver.Dim_Geografia g 
    ON f.ID_Geografia = g.ID_Geografia
LEFT JOIN Silver.Dim_Sector_Catalogo s ON g.ID_Sector_Catalogo = s.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo m ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo tu ON g.ID_Turno_Catalogo = tu.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo va ON g.ID_Valvula_Catalogo = va.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo ca ON g.ID_Cama_Catalogo = ca.ID_Cama_Catalogo
INNER JOIN Silver.Dim_Campana c 
    ON f.ID_Campana = c.ID_Campana
-- Hacemos LEFT JOIN con el bridge para saber si esa geografía estaba viva en esa campaña
LEFT JOIN Silver.Bridge_Geografia_Campana bgc 
    ON f.ID_Geografia = bgc.ID_Geografia 
   AND f.ID_Campana = bgc.ID_Campana
WHERE f.Estado_DQ = 'OK';
GO
