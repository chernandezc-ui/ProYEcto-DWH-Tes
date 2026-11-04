-- =============================================================================
-- FASE 26: Vista emuladora Silver.vDim_Geografia
-- Reconstruye la interfaz monolítica de Silver.Dim_Geografia desde el modelo
-- normalizado de catálogos (Dim_Geografia_Nueva + 6 Dim_*_Catalogo).
--
-- PROPÓSITO: permite que lookup.py, Gold marts, Power BI y cualquier
-- consumidor existente sigan funcionando sin cambios cuando se haga el
-- rename Dim_Geografia → Dim_Geografia_Obsoleta en una iteración futura.
--
-- PRECONDICIÓN: Fase 25 ya ejecutada (tablas de catálogos existentes).
-- NO modifica Silver.Dim_Geografia ni ninguna tabla de hechos.
-- =============================================================================

CREATE OR ALTER VIEW Silver.vDim_Geografia AS
SELECT
    -- PK: mismo dominio de claves que Dim_Geografia
    g.ID_Geografia,

    -- Textos planos reconstruidos desde catálogos
    f.Fundo,
    sc.Sector,
    mc.Modulo,
    mc.SubModulo,
    mc.Tipo_Conduccion,
    tc.Turno,
    vc.Valvula,
    cc.Cama_Normalizada                         AS Cama,

    -- Atributos de la junk dimension
    g.Es_Test_Block,
    g.Codigo_SAP_Campo,
    g.Nivel_Granularidad,

    -- SCD Tipo 2
    g.Fecha_Inicio_Vigencia,
    g.Fecha_Fin_Vigencia,
    g.Es_Vigente

FROM Silver.Dim_Geografia_Nueva         g
JOIN Silver.Dim_Fundo_Catalogo          f  ON f.ID_Fundo_Catalogo   = g.ID_Fundo_Catalogo
JOIN Silver.Dim_Sector_Catalogo         sc ON sc.ID_Sector_Catalogo  = g.ID_Sector_Catalogo
JOIN Silver.Dim_Modulo_Catalogo         mc ON mc.ID_Modulo_Catalogo  = g.ID_Modulo_Catalogo
JOIN Silver.Dim_Turno_Catalogo          tc ON tc.ID_Turno_Catalogo   = g.ID_Turno_Catalogo
JOIN Silver.Dim_Valvula_Catalogo        vc ON vc.ID_Valvula_Catalogo = g.ID_Valvula_Catalogo
JOIN Silver.Dim_Cama_Catalogo           cc ON cc.ID_Cama_Catalogo    = g.ID_Cama_Catalogo;
GO

-- =============================================================================
-- Verificación rápida post-deploy (ejecutar manualmente):
--
-- -- Paridad de filas vigentes
-- SELECT COUNT(*) AS n_vieja FROM Silver.Dim_Geografia  WHERE Es_Vigente = 1;
-- SELECT COUNT(*) AS n_vista  FROM Silver.vDim_Geografia WHERE Es_Vigente = 1;
--
-- -- Muestra de 20 filas para revisión visual
-- SELECT TOP 20 * FROM Silver.vDim_Geografia ORDER BY ID_Geografia;
--
-- -- Verificar que lookup.py no pierda resoluciones:
-- SELECT v.ID_Geografia, v.Fundo, v.Sector, v.Modulo, v.SubModulo,
--        v.Turno, v.Valvula, v.Cama, v.Es_Test_Block
-- FROM Silver.vDim_Geografia v
-- WHERE v.Es_Vigente = 1
-- ORDER BY v.ID_Geografia;
-- =============================================================================
