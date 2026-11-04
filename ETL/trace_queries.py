import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config.conexion import obtener_engine
from sqlalchemy import text

def trace_running_queries():
    engine = obtener_engine()
    with engine.connect() as conn:
        res = conn.execute(text("""
            SELECT 
                r.session_id,
                r.status,
                r.command,
                r.wait_type,
                r.wait_time,
                r.blocking_session_id,
                t.text AS current_query
            FROM sys.dm_exec_requests r
            CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) t
            WHERE r.session_id <> @@SPID
              AND r.session_id > 50
        """)).fetchall()
        
        if not res:
            print("No active queries found.")
            
        for r in res:
            print(f"SPID: {r.session_id}")
            print(f"Status: {r.status}")
            print(f"Command: {r.command}")
            print(f"Wait Type: {r.wait_type}")
            print(f"Wait Time: {r.wait_time} ms")
            print(f"Blocking SPID: {r.blocking_session_id}")
            print(f"Query: {r.current_query[:200]}")
            print("-" * 50)

if __name__ == '__main__':
    trace_running_queries()
