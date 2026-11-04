"""
fix_evaluacion_vegetativa.py
============================
Corrección y reprocesamiento integral del pipeline de Evaluación Vegetativa:
 1. Trunca las tablas Bronce, Silver y Gold de Evaluación Vegetativa.
 2. Elimina la cuarentena previa para limpiar logs.
 3. Copia el archivo Excel histórico a data/entrada/evaluacion_vegetativa_v2/
 4. Ejecuta la carga a Bronce aplicando los nuevos alias de mapeo de pisos.
 5. Ejecuta el reprocesamiento a Silver usando el procesador limpio del usuario.
 6. Refresca la tabla Gold de Mart de forma segura.

Ejecutar con: python tools/fix_evaluacion_vegetativa.py
"""
import sys, os
import shutil
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.conexion import obtener_engine
from sqlalchemy import text
from bronce.cargador import cargar_archivo
from silver.facts.fact_evaluacion_vegetativa import cargar_fact_evaluacion_vegetativa
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
log = logging.getLogger("fix_ev_completo")

engine = obtener_engine()

# Rutas de archivos
ETL_DIR = Path(__file__).resolve().parent.parent
EXCEL_ORIGEN = ETL_DIR / "data" / "procesados" / "evaluacion_vegetativa" / "historico_vegetativa_20260528_094026_20260528_113437.xlsx"
CARPETA_ENTRADA_V2 = ETL_DIR / "data" / "entrada" / "evaluacion_vegetativa_v2"
EXCEL_DESTINO = CARPETA_ENTRADA_V2 / "historico_vegetativa.xlsx"

# 1. Truncar tablas
log.info("PASO 1: Truncando tablas en la base de datos...")
with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE Gold.Mart_Evaluacion_Vegetativa;"))
    log.info("  [OK] Gold.Mart_Evaluacion_Vegetativa truncada.")
    conn.execute(text("DELETE FROM Silver.Fact_Evaluacion_Vegetativa;"))
    log.info("  [OK] Silver.Fact_Evaluacion_Vegetativa limpia.")
    conn.execute(text("DELETE FROM Bronce.Evaluacion_Vegetativa;"))
    log.info("  [OK] Bronce.Evaluacion_Vegetativa limpia.")
    
    # Limpiar cuarentena
    conn.execute(text("""
        DELETE FROM MDM.Cuarentena 
        WHERE Tabla_Origen IN ('Bronce.Evaluacion_Vegetativa', 'Silver.Fact_Evaluacion_Vegetativa')
    """))
    log.info("  [OK] Cuarentena limpia para Evaluación Vegetativa.")

# 2. Copiar archivo a entrada
log.info("\nPASO 2: Copiando Excel histórico a la carpeta de entrada...")
if not EXCEL_ORIGEN.exists():
    log.error(f"  [ERROR] No se encuentra el archivo origen: {EXCEL_ORIGEN}")
    sys.exit(1)

CARPETA_ENTRADA_V2.mkdir(parents=True, exist_ok=True)
shutil.copy2(EXCEL_ORIGEN, EXCEL_DESTINO)
log.info(f"  [OK] Copiado a: {EXCEL_DESTINO}")

# 3. Cargar Bronce
log.info("\nPASO 3: Cargando archivo a Bronce.Evaluacion_Vegetativa...")
res_bronce = cargar_archivo(
    nombre_carpeta="evaluacion_vegetativa_v2",
    ruta_archivo=EXCEL_DESTINO,
    tabla_destino="Bronce.Evaluacion_Vegetativa",
    engine=engine
)
log.info(f"  Estado de carga: {res_bronce.get('estado')}")
log.info(f"  Filas insertadas en Bronce: {res_bronce.get('filas', 0):,}")
log.info(f"  Mensaje: {res_bronce.get('mensaje')}")

if res_bronce.get('estado') != 'OK':
    log.error("  [ERROR] La carga a Bronce falló.")
    sys.exit(1)

# 4. Procesar Silver
log.info("\nPASO 4: Procesando Silver.Fact_Evaluacion_Vegetativa desde Bronce...")
# Corremos el procesador Silver de Evaluación Vegetativa.
# Como es una llamada directa, no disparará el circuit breaker del pipeline general.
resumen_silver = cargar_fact_evaluacion_vegetativa(engine)
log.info(f"  Leídos:     {resumen_silver.get('Filas_Leidas_Bronce', 0):,}")
log.info(f"  Insertados: {resumen_silver.get('Filas_Insertadas', 0):,}")
log.info(f"  Rechazados: {resumen_silver.get('Nuevos_Casos_Cuarentena', 0):,}")

# 5. Refrescar Gold
log.info("\nPASO 5: Refrescando Gold.Mart_Evaluacion_Vegetativa...")
SQL_INSERT_GOLD = """
INSERT INTO Gold.Mart_Evaluacion_Vegetativa (
    ID_Tiempo, ID_Geografia, ID_Variedad, ID_Campana,
    Fundo, Modulo, Variedad,
    Semana_ISO, Piso,
    Semanas_Despues_Poda_Promedio,
    Altura_Promedio,
    Tallos_Basales_Promedio,
    Tallos_Basales_Nuevos_Promedio,
    Muestra_Plantas_Total,
    Brotes_Generales_Promedio,
    Brotes_Productivos_Promedio,
    Diametro_Brote_Promedio,
    N_Muestras,
    Fecha_Actualizacion
)
SELECT
    f.ID_Tiempo,
    f.ID_Geografia,
    f.ID_Variedad,
    f.ID_Campana,
    ISNULL(fundo.Fundo, 'SIN_FUNDO')               AS Fundo,
    ISNULL(mod_cat.Modulo, 0)                       AS Modulo,
    ISNULL(var.Nombre_Variedad, 'SIN_VARIEDAD')     AS Variedad,
    t.Semana_ISO,
    f.Piso,
    AVG(CAST(f.Semanas_Despues_Poda AS DECIMAL(10,2))) AS Semanas_Despues_Poda_Promedio,
    AVG(f.Altura)                                   AS Altura_Promedio,
    AVG(f.Tallos_Basales)                           AS Tallos_Basales_Promedio,
    AVG(f.Tallos_Basales_Nuevos)                    AS Tallos_Basales_Nuevos_Promedio,
    SUM(f.Muestra_Plantas)                          AS Muestra_Plantas_Total,
    AVG(f.Brotes_Generales)                         AS Brotes_Generales_Promedio,
    AVG(f.Brotes_Productivos)                       AS Brotes_Productivos_Promedio,
    AVG(f.Diametro_Brote)                           AS Diametro_Brote_Promedio,
    COUNT(*)                                        AS N_Muestras,
    GETDATE()                                       AS Fecha_Actualizacion
FROM Silver.Fact_Evaluacion_Vegetativa f
JOIN Silver.Dim_Tiempo t
    ON f.ID_Tiempo = t.ID_Tiempo
LEFT JOIN Silver.Dim_Geografia geo
    ON f.ID_Geografia = geo.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo fundo
    ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mod_cat
    ON geo.ID_Modulo_Catalogo = mod_cat.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Variedad var
    ON f.ID_Variedad = var.ID_Variedad
WHERE f.Estado_DQ = 'OK'
GROUP BY
    f.ID_Tiempo, f.ID_Geografia, f.ID_Variedad, f.ID_Campana,
    ISNULL(fundo.Fundo, 'SIN_FUNDO'),
    ISNULL(mod_cat.Modulo, 0),
    ISNULL(var.Nombre_Variedad, 'SIN_VARIEDAD'),
    t.Semana_ISO,
    f.Piso;
"""
with engine.begin() as conn:
    r = conn.execute(text(SQL_INSERT_GOLD))
    log.info(f"  Gold.Mart_Evaluacion_Vegetativa: {r.rowcount:,} filas insertadas.")

# 6. Verificación Final
log.info("\n=== VERIFICACIÓN FINAL ===")
with engine.connect() as conn:
    s_cnt  = conn.execute(text("SELECT COUNT(*) FROM Silver.Fact_Evaluacion_Vegetativa")).scalar()
    g_cnt  = conn.execute(text("SELECT COUNT(*) FROM Gold.Mart_Evaluacion_Vegetativa")).scalar()
    bg_ok  = conn.execute(text("SELECT COUNT(*) FROM Silver.Fact_Evaluacion_Vegetativa WHERE Brotes_Generales > 0")).scalar()
    bp_ok  = conn.execute(text("SELECT COUNT(*) FROM Silver.Fact_Evaluacion_Vegetativa WHERE Brotes_Productivos > 0")).scalar()
    alt_ok = conn.execute(text("SELECT COUNT(*) FROM Silver.Fact_Evaluacion_Vegetativa WHERE Altura > 0")).scalar()

log.info(f"  Silver total:             {s_cnt:,}")
log.info(f"  Silver con Altura > 0:    {alt_ok:,}")
log.info(f"  Silver con BrotesGen > 0: {bg_ok:,}")
log.info(f"  Silver con BrotesProd > 0:{bp_ok:,}")
log.info(f"  Gold total:               {g_cnt:,}")

log.info("\n✅ ¡Reprocesamiento y corrección de Evaluación Vegetativa completado con éxito!")
