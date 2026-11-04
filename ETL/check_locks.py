import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config.conexion import obtener_engine
from sqlalchemy import text

def check_locks():
    engine = obtener_engine()
    with engine.connect() as conn:
        res = conn.execute(text("""
            SELECT 
                request_session_id AS spid, 
                resource_type, 
                DB_NAME(resource_database_id) as dbname,
                OBJECT_NAME(resource_associated_entity_id) as object_name, 
                request_mode, 
                request_status 
            FROM sys.dm_tran_locks 
            WHERE resource_type = 'OBJECT'
        """)).fetchall()
        for r in res:
            print(r)

if __name__ == '__main__':
    check_locks()
