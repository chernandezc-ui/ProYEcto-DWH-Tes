/* ============================================================================
   Fase 20 — Vistas legibles para Power BI (capa de consumo sobre Gold)
   Reemplaza IDs crudos por columnas legibles. Idempotente.
   ========================================================================== */

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'PowerBI')
    EXEC('CREATE SCHEMA PowerBI');
GO

CREATE OR ALTER VIEW PowerBI.vw_Cosecha AS
SELECT
    m.ID_Mart_Cosecha,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Turno, m.Condicion, m.Fecha_Cosecha, m.Fecha_Evento,
    m.Kg_Neto_Real, m.Kg_Brutos, m.Kg_Neto_MP, m.Kg_Proyectados, m.Kg_Proyectado,
    m.Pct_Cumplimiento, m.Cantidad_Jabas, m.Peso_Promedio_Jaba_kg,
    m.Fecha_Actualizacion
FROM Gold.Mart_Cosecha m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO

CREATE OR ALTER VIEW PowerBI.vw_Censo_Plantas AS
SELECT
    m.ID_Mart_Censo,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Estado_Planta, m.Cantidad, m.Linea_Raw,
    m.Fecha_Actualizacion
FROM Gold.Mart_Censo_Plantas m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO

CREATE OR ALTER VIEW PowerBI.vw_Ciclo_Poda AS
SELECT
    m.ID_Mart_Poda,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Tipo_Evaluacion,
    m.Tallos_Planta_Total, m.Longitud_Tallo_Total, m.Diametro_Tallo_Total,
    m.Ramilla_Planta_Total, m.Tocones_Planta_Total, m.Cortes_Defectuosos_Total,
    m.Altura_Poda_Total, m.N_Muestras,
    m.Fecha_Actualizacion
FROM Gold.Mart_Ciclo_Poda m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO

CREATE OR ALTER VIEW PowerBI.vw_Evaluacion_Vegetativa AS
SELECT
    m.ID_Mart_Vegetativa,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Piso,
    m.Semanas_Despues_Poda_Promedio, m.Altura_Promedio,
    m.Tallos_Basales_Promedio, m.Tallos_Basales_Nuevos_Promedio,
    m.Muestra_Plantas_Total, m.Brotes_Generales_Promedio,
    m.Brotes_Productivos_Promedio, m.Diametro_Brote_Promedio,
    m.Ratio_Productivo_General, m.N_Muestras,
    m.Fecha_Actualizacion
FROM Gold.Mart_Evaluacion_Vegetativa m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO

CREATE OR ALTER VIEW PowerBI.vw_Fisiologia AS
SELECT
    m.ID_Mart_Fisiologia,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Tercio,
    m.Brotes_Productivos_Promedio, m.Brotes_Vegetativos_Promedio,
    m.Hinchadas_Promedio, m.Productivas_Promedio,
    m.Total_Organos_Promedio, m.Ratio_Productivo_Veg,
    m.Fecha_Actualizacion
FROM Gold.Mart_Fisiologia m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO

CREATE OR ALTER VIEW PowerBI.vw_Induccion_Floral AS
SELECT
    m.ID_Mart_Induccion,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Tipo_Evaluacion,
    m.Pct_Plantas_Con_Induccion_Prom, m.Pct_Brotes_Con_Induccion_Prom,
    m.Pct_Brotes_Con_Flor_Prom, m.Brotes_Totales, m.Brotes_Con_Flor,
    m.Fecha_Actualizacion
FROM Gold.Mart_Induccion_Floral m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO

CREATE OR ALTER VIEW PowerBI.vw_Tasa_Crecimiento AS
SELECT
    m.ID_Mart_Crecimiento,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Tipo_Evaluacion, m.Estado_Vegetativo, m.Tipo_Tallo,
    m.Medida_Crecimiento_Promedio, m.Medida_Crecimiento_Max,
    m.Dias_Desde_Poda_Promedio, m.Cantidad_Mediciones,
    m.Fecha_Actualizacion
FROM Gold.Mart_Tasa_Crecimiento m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO

CREATE OR ALTER VIEW PowerBI.vw_Pesos_Calibres AS
SELECT
    m.ID_Mart_Pesos,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Evaluador,
    m.Cant_Bayas_Muestra, m.Peso_Promedio_Baya_g, m.Peso_Proyectado_Baya_g,
    m.Tendencia_Peso, m.Estado_DQ,
    m.Fecha_Actualizacion
FROM Gold.Mart_Pesos_Calibres m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO

CREATE OR ALTER VIEW PowerBI.vw_Proyecciones AS
SELECT
    m.ID_Mart_Proyeccion,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    m.Semana_Objetivo,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    m.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    es.Tipo_Escenario, es.Descripcion AS Descripcion_Escenario,
    m.Version_Escenario, m.Version_Modelo, m.Estado_Workflow,
    m.Fecha_Generacion, m.Fecha_Cutoff,
    m.Kg_Proyectados, m.Kg_Real, m.Error_MAPE, m.MAPE, m.Desviacion_kg,
    m.Flag_Override, m.Motivo_Override,
    m.Fecha_Actualizacion
FROM Gold.Mart_Proyecciones m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Escenario_Proyeccion es ON m.ID_Escenario = es.ID_Escenario
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO

CREATE OR ALTER VIEW PowerBI.vw_Maduracion AS
SELECT
    m.ID_Mart_Maduracion,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    COALESCE(ef.Nombre_Estado, m.Estado_Fenologico) AS Estado_Fenologico,
    ef.Orden_Estado,
    COALESCE(ci.Color_Cinta, m.Color_Cinta) AS Color_Cinta,
    m.Organos_Observados, m.Dias_Pasados_Promedio,
    m.Fecha_Actualizacion
FROM Gold.Mart_Maduracion m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Estado_Fenologico ef ON m.ID_Estado_Fenologico = ef.ID_Estado_Fenologico
LEFT JOIN Silver.Dim_Cinta    ci ON m.ID_Cinta    = ci.ID_Cinta
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO

CREATE OR ALTER VIEW PowerBI.vw_Clima AS
SELECT
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    m.Sector_Climatico,
    m.Temp_Promedio_Diaria, m.Temp_Maxima_Dia, m.Temp_Minima_Dia,
    m.Humedad_Promedio, m.Precipitacion_Total,
    m.Indice_UV_Max, m.Indice_UV_Min,
    m.Radiacion_Solar_Prom_Diurna, m.Radiacion_Solar_Max,
    m.VPD_Promedio, m.GDD
FROM Gold.Mart_Clima m
LEFT JOIN Silver.Dim_Tiempo  t  ON m.ID_Tiempo  = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana ca ON m.ID_Campana = ca.ID_Campana;
GO

CREATE OR ALTER VIEW PowerBI.vw_Administrativo AS
SELECT
    m.ID_Mart_Admin,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes,
    COALESCE(t.Semana_ISO, m.Semana_ISO) AS Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(p.Nombre_Completo, m.Nombre_Personal) AS Nombre_Personal,
    COALESCE(p.DNI, m.DNI_Personal) AS DNI_Personal,
    m.Sexo, m.Rol, m.Supervisor,
    COALESCE(ao.Nombre_Actividad, m.Actividad) AS Actividad,
    COALESCE(ao.Nombre_Labor, m.Labor) AS Labor,
    ao.Categoria,
    m.Horas_Trabajadas, m.Horas_Trabajadas_Total, m.Dias_Trabajados,
    m.Pct_Asertividad, m.Registros_Observados_SAP,
    m.Fecha_Actualizacion
FROM Gold.Mart_Administrativo m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Personal p  ON m.ID_Personal = p.ID_Personal
LEFT JOIN Silver.Dim_Actividad_Operativa ao ON m.ID_Actividad = ao.ID_Actividad;
GO

CREATE OR ALTER VIEW PowerBI.vw_Fenologia AS
SELECT
    m.ID_Mart_Fenologia,
    m.Semana_ISO, m.Modulo, m.Variedad, m.Color_Cinta,
    m.Estado_Fenologico, m.Orden_Estado,
    m.Cantidad_Bayas, m.Pct_Cosechable, m.Pct_Avance_Ciclo,
    m.Brotes_Productivos, m.Brotes_Vegetativos, m.Ratio_Productivo_Veg,
    m.Fecha_Actualizacion
FROM Gold.Mart_Fenologia m;
GO
