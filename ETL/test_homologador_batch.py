import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config.conexion import obtener_engine
from sqlalchemy import text
from utils.contexto_transaccional import ContextoTransaccionalETL
from mdm.homologador import registrar_homologaciones_batch

def test_batch():
    engine = obtener_engine()
    pendientes = [
        {'texto_crudo': 'VENTURA TEST', 'valor_canonico': 'VENTURA', 'estado': 'APROBADA', 'score': 1.0},
        {'texto_crudo': 'BILOXI TEST', 'valor_canonico': 'BILOXI', 'estado': 'APROBADA', 'score': 1.0}
    ]
    print("Testing registrar_homologaciones_batch inside transaction")
    try:
        with ContextoTransaccionalETL(engine) as contexto:
            registrar_homologaciones_batch(contexto._conexion_activa(), 'TestTable', 'Variedad_Raw', pendientes)
        print("Success inside transaction")
    except Exception as e:
        print(f"Error inside transaction: {e}")

if __name__ == '__main__':
    test_batch()
