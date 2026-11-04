import sys
import logging

import os
from config.conexion import obtener_engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger("LiberarCuarentena")

def liberar_cuarentena():
    engine = obtener_engine()
    
    with engine.begin() as conn:
        # 1. Identificar tablas y registros afectados
        log.info("Buscando registros en cuarentena por falta de campaña...")
        sql_pendientes = """
            SELECT DISTINCT Tabla_Origen, ID_Registro_Origen, ID_Cuarentena
            FROM MDM.Cuarentena
            WHERE Motivo LIKE '%campaña activa%' OR Motivo LIKE '%Bridge%'
        """
        pendientes = conn.execute(text(sql_pendientes)).fetchall()
        
        if not pendientes:
            log.info("No se encontraron registros para liberar.")
            return

        log.info(f"Se encontraron {len(pendientes)} registros para liberar.")
        
        # Agrupar por tabla para eficiencia
        por_tabla = {}
        for row in pendientes:
            por_tabla.setdefault(row.Tabla_Origen, []).append(row.ID_Registro_Origen)
            
        # 2. Resetear en Bronce
        MAPA_PK = {
            'Bronce.Fisiologia': 'ID_Fisiologia',
            'Bronce.Tasa_Crecimiento_Brotes': 'ID_Tasa_Crecimiento',
            'Bronce.Induccion_Floral': 'ID_Induccion_Floral',
            'Bronce.Floracion': 'ID_Evaluacion_Vegetativa',
            'Bronce.Conteo_Fruta': 'ID_Conteo_Fruta',
            'Bronce.Peladas': 'ID_Peladas',
            'Bronce.Reporte_Cosecha': 'ID_Reporte_Cosecha',
            'Bronce.Data_SAP': 'ID_SAP',
            'Bronce.Evaluacion_Pesos': 'ID_Evaluacion_Pesos',
            'Bronce.Consolidado_Tareos': 'ID_Consolidado_Tareos',
            'Bronce.Seguimiento_Errores': 'ID_Seguimiento_Errores',
            'Bronce.Evaluacion_Calidad_Poda': 'ID_Evaluacion_Poda'
        }
        
        for tabla, ids in por_tabla.items():
            pk = MAPA_PK.get(tabla)
            if not pk:
                log.warning(f"No se conoce la PK para {tabla}. Saltando.")
                continue
                
            log.info(f"Liberando {len(ids)} registros en {tabla} ({pk})...")
            # SQL Server limits: split in batches of 1000
            for i in range(0, len(ids), 1000):
                lote = ids[i:i+1000]
                conn.execute(text(f"UPDATE {tabla} SET Estado_Carga = 'CARGADO' WHERE {pk} IN ({','.join(map(str, lote))})"))

        # 3. Limpiar Cuarentena
        log.info("Limpiando tabla MDM.Cuarentena...")
        conn.execute(text("""
            DELETE FROM MDM.Cuarentena
            WHERE Motivo LIKE '%campaña activa%' OR Motivo LIKE '%Bridge%'
        """))
        
        log.info("Proceso completado con éxito.")

if __name__ == "__main__":
    liberar_cuarentena()
