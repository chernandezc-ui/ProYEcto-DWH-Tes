import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config.conexion import obtener_engine
from utils.contexto_transaccional import ContextoTransaccionalETL
from silver.facts.fact_tasa_crecimiento_brotes import ProcesadorTasaCrecimientoBrotes
from mdm.homologador import homologar_columna
import logging

logging.basicConfig(level=logging.INFO)

def test():
    engine = obtener_engine()
    proc = ProcesadorTasaCrecimientoBrotes(engine, columna_id='ID_Tasa_Crecimiento')
    
    cols_raw = [
        'Fecha_Raw', 'DNI_Raw', 'Evaluador_Raw', 'Modulo_Raw', 'Turno_Raw',
        'Valvula_Raw', 'Cama_Raw', 'Variedad_Raw', 'Estado_Vegetativo_Raw',
        'Valores_Raw',
    ]
    print("Reading Bronce...")
    df = proc.leer_bronce(cols_raw)
    print(f"Loaded {len(df)} rows")
    
    # Take a small sample to see if it's just slow or actually hanging
    df_sample = df.head(5000).copy()
    
    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()
        print("Homologando...")
        df_sample, cuar_var = homologar_columna(
            df_sample, 'Variedad_Raw', 'Variedad_Canonica', 'Bronce.Tasa_Crecimiento_Brotes', conexion,
            columna_id_origen='ID_Tasa_Crecimiento',
        )
        
        print("Construyendo payload...")
        t0 = time.time()
        payload = proc._construir_payload(df_sample)
        t1 = time.time()
        print(f"Payload built for {len(df_sample)} rows in {t1-t0:.2f} seconds")
        if len(df_sample) > 0:
            print(f"Extrapolating for 418K rows: {(t1-t0)*418000/len(df_sample)/60:.2f} minutes")
        
        print("Executing insercion_masiva_segura...")
        t0 = time.time()
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_TasaCrecimientoBrotes')
        t1 = time.time()
        print(f"Insercion masiva executed in {t1-t0:.2f} seconds")
        if len(df_sample) > 0:
            print(f"Extrapolating for 418K rows: {(t1-t0)*418000/len(df_sample)/60:.2f} minutes")

if __name__ == '__main__':
    test()
