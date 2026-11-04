-- =============================================================================
-- fase48c_v2_vista_gold_vegetativa.sql
-- =============================================================================
-- Reemplaza Gold.vw_Analitica_Evaluacion_Vegetativa_Campana con:
--   + ID_Geografia, ID_Campana, ID_Variedad, ID_Tiempo (IDs numericos para PBI)
--   + Fundo (estaba ausente)
--   + Es_Geografia_Vigente_SCD2 (flag SCD2 desde Dim_Geografia)
--   + Es_Geografia_Valida_En_Campana (flag desde Bridge_Geografia_Campana)
--   + Codigo_SAP_Campo (util para conciliar con SAP)
--   + Nivel_Granularidad (cama/valvula/turno/modulo)
--
-- Cambios estructurales vs fase48c:
--   - INNER JOIN Dim_Campana -> LEFT JOIN (la sentinel SIN_CAMPANA queda visible)
--   - JOIN al bridge: si la geo no aparece en el bridge para esa campaña,
--     Es_Geografia_Valida_En_Campana = 0 (no NULL silencioso).
--
-- Pre-requisitos: fase48b ejecutada (bridge poblado).
-- =============================================================================
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER VIEW Gold.vw_Analitica_Evaluacion_Vegetativa_Campana
AS
SELECT
    -- ============ Identificadores numericos (para PBI joins / filtros) ============
    f.ID_Fact_Evaluacion_Vegetativa,
    f.ID_Geografia,
    f.ID_Campana,
    f.ID_Variedad,
    f.ID_Tiempo,

    -- ============ Hechos ============
    f.Piso,
    f.Brotes_Generales,
    f.Brotes_Productivos,
    f.Diametro_Brote,
    f.Altura,
    f.Tallos_Basales,
    f.Tallos_Basales_Nuevos,
    f.Semanas_Despues_Poda,
    f.Fecha_Evento,

    -- ============ Dimension Tiempo ============
    t.Fecha       AS Tiempo_Fecha,
    t.Anio        AS Tiempo_Anio,
    t.Mes         AS Tiempo_Mes,
    t.Semana_ISO  AS Tiempo_Semana,
    t.Nombre_Mes  AS Tiempo_Nombre_Mes,

    -- ============ Dimension Variedad ============
    v.Nombre_Variedad,

    -- ============ Dimension Geografia (expandida + flags) ============
    fu.Fundo,
    s.Sector,
    m.Modulo,
    m.SubModulo,
    tu.Turno,
    va.Valvula,
    ca.Cama_Normalizada           AS Cama,
    g.Codigo_SAP_Campo,
    g.Nivel_Granularidad,
    g.Es_Vigente                  AS Es_Geografia_Vigente_SCD2,

    -- ============ Dimension Campana (el slicer) ============
    c.Nombre_Campana,
    c.Anio_Cosecha                AS Campana_Anio_Cosecha,
    c.Fecha_Inicio_Poda           AS Campana_Fecha_Inicio_Poda,
    c.Fecha_Inicio_Campana        AS Campana_Fecha_Inicio,
    c.Fecha_Fin_Campana           AS Campana_Fecha_Fin,
    c.Es_Vigente_Operacion        AS Campana_En_Curso,

    -- ============ Flag Bridge ============
    -- 1 = la (geografia, campana) existe en Bridge_Geografia_Campana
    -- 0 = no aparece (anomalia: fact tiene un par que el bridge no conoce)
    CAST(CASE WHEN bgc.ID_Bridge IS NULL THEN 0 ELSE 1 END AS BIT)
        AS Es_Geografia_Valida_En_Campana,
    bgc.Vigencia_Inicio           AS Bridge_Vigencia_Inicio,
    bgc.Vigencia_Fin              AS Bridge_Vigencia_Fin

FROM Silver.Fact_Evaluacion_Vegetativa f
INNER JOIN Silver.Dim_Tiempo    t  ON t.ID_Tiempo    = f.ID_Tiempo
INNER JOIN Silver.Dim_Variedad  v  ON v.ID_Variedad  = f.ID_Variedad
INNER JOIN Silver.Dim_Geografia g  ON g.ID_Geografia = f.ID_Geografia
LEFT  JOIN Silver.Dim_Fundo_Catalogo   fu ON fu.ID_Fundo_Catalogo   = g.ID_Fundo_Catalogo
LEFT  JOIN Silver.Dim_Sector_Catalogo  s  ON s.ID_Sector_Catalogo   = g.ID_Sector_Catalogo
LEFT  JOIN Silver.Dim_Modulo_Catalogo  m  ON m.ID_Modulo_Catalogo   = g.ID_Modulo_Catalogo
LEFT  JOIN Silver.Dim_Turno_Catalogo   tu ON tu.ID_Turno_Catalogo   = g.ID_Turno_Catalogo
LEFT  JOIN Silver.Dim_Valvula_Catalogo va ON va.ID_Valvula_Catalogo = g.ID_Valvula_Catalogo
LEFT  JOIN Silver.Dim_Cama_Catalogo    ca ON ca.ID_Cama_Catalogo    = g.ID_Cama_Catalogo
-- LEFT JOIN a Dim_Campana: si ID_Campana=0 (SIN_CAMPANA), la fila queda visible.
LEFT  JOIN Silver.Dim_Campana c  ON c.ID_Campana  = f.ID_Campana
LEFT  JOIN Silver.Bridge_Geografia_Campana bgc
       ON bgc.ID_Geografia = f.ID_Geografia
      AND bgc.ID_Campana   = f.ID_Campana
WHERE f.Estado_DQ = 'OK';
GO

-- -----------------------------------------------------------------------------
-- Smoke tests sobre la vista
-- -----------------------------------------------------------------------------
DECLARE @total INT, @con_camp INT, @con_bridge INT, @con_fundo INT;

SELECT @total      = COUNT(*),
       @con_camp   = SUM(CASE WHEN Nombre_Campana          IS NOT NULL THEN 1 ELSE 0 END),
       @con_bridge = SUM(CASE WHEN Es_Geografia_Valida_En_Campana = 1 THEN 1 ELSE 0 END),
       @con_fundo  = SUM(CASE WHEN Fundo                   IS NOT NULL THEN 1 ELSE 0 END)
  FROM Gold.vw_Analitica_Evaluacion_Vegetativa_Campana;

SELECT
    Filas_Vista              = @total,
    Filas_Con_Campana        = @con_camp,
    Filas_Con_Bridge_Activo  = @con_bridge,
    Filas_Con_Fundo          = @con_fundo;

-- Distribucion por campania (debe mostrar al menos 1 campania con datos)
SELECT TOP 5
    Nombre_Campana,
    Campana_Anio_Cosecha,
    COUNT(*) AS Filas
  FROM Gold.vw_Analitica_Evaluacion_Vegetativa_Campana
 GROUP BY Nombre_Campana, Campana_Anio_Cosecha
 ORDER BY Filas DESC;

-- Sanity: muestra 3 filas
SELECT TOP 3
    ID_Fact_Evaluacion_Vegetativa, Fundo, Sector, Modulo, Valvula, Cama,
    Nombre_Campana, Campana_Anio_Cosecha,
    Es_Geografia_Vigente_SCD2, Es_Geografia_Valida_En_Campana,
    Piso, Brotes_Productivos, Fecha_Evento
  FROM Gold.vw_Analitica_Evaluacion_Vegetativa_Campana
 ORDER BY Fecha_Evento DESC;
GO

PRINT 'fase48c_v2: vista Gold recreada con Fundo, IDs numericos y flags SCD2/Bridge.';
GO
