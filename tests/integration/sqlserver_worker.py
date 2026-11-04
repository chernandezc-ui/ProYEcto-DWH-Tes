"""Executed by sqlserver_e2e.py with an isolated environment, no mocks."""
from pathlib import Path
import json
import os
import sys
from sqlalchemy import text

ROOT=Path(__file__).resolve().parents[2]
ART=ROOT/'.test-tmp-sqlserver'
WORK=ART/'workspace'
sys.path[:0]=[str(WORK/'ETL'), str(WORK/'backend'), str(WORK)]
from comun.conexion import obtener_engine
from tools import migration_runner


def main():
    expected=os.environ['DB_NOMBRE']
    assert expected.startswith('ACP_E2E_')
    engine=obtener_engine()
    with engine.begin() as con:
        assert con.execute(text('SELECT DB_NAME()')).scalar()==expected
        assert con.execute(text("SELECT IS_SRVROLEMEMBER('sysadmin')")).scalar()==0
        con.execute(text("IF OBJECT_ID('dbo.E2E_Migration_Probe','U') IS NULL CREATE TABLE dbo.E2E_Migration_Probe(value INT)"))
        con.execute(text('DELETE FROM dbo.E2E_Migration_Probe'))
    good=ART/'e2e_migration_good.sql'
    good.write_bytes(b"-- comments must not hide SQL\r\nINSERT INTO dbo.E2E_Migration_Probe VALUES (10);\r\ngo\r\nINSERT INTO dbo.E2E_Migration_Probe VALUES (20);\r\nGO\r\n")
    result=migration_runner._aplicar_migracion(engine,good,migration_runner._calcular_hash(good))
    assert result['estado']=='OK',result
    bad=ART/'e2e_migration_delayed_error.sql'
    bad.write_text("INSERT INTO dbo.E2E_Migration_Probe VALUES (99); PRINT 'first result'; RAISERROR('E2E delayed ODBC failure',16,1);")
    result=migration_runner._aplicar_migracion(engine,bad,migration_runner._calcular_hash(bad))
    assert result['estado']=='ERROR',result
    audit=ART/'e2e_migration_audit_failure.sql'
    audit.write_text('INSERT INTO dbo.E2E_Migration_Probe VALUES (999);')
    with engine.begin() as con:
        migration_runner._ejecutar_batch(con,"""CREATE OR ALTER TRIGGER Admin.E2E_Reject_Audit
        ON Admin.Migraciones_Aplicadas AFTER INSERT, UPDATE AS BEGIN
          IF EXISTS (SELECT 1 FROM inserted WHERE Nombre_Archivo='e2e_migration_audit_failure.sql' AND Estado='OK')
            THROW 51002, 'Synthetic audit write failure', 1;
        END""")
    try:
        audit_result=migration_runner._aplicar_migracion(engine,audit,migration_runner._calcular_hash(audit))
        assert audit_result['estado']=='ERROR',audit_result
    finally:
        with engine.begin() as con:
            migration_runner._ejecutar_batch(con,'DROP TRIGGER IF EXISTS Admin.E2E_Reject_Audit')
    with engine.connect() as con:
        values=[r[0] for r in con.execute(text('SELECT value FROM dbo.E2E_Migration_Probe ORDER BY value'))]
        assert values==[10,20],values
        ledger=dict(con.execute(text("SELECT Nombre_Archivo,Estado FROM Admin.Migraciones_Aplicadas WHERE Nombre_Archivo LIKE 'e2e_migration_%'" )).all())
        assert ledger[good.name]=='OK' and ledger[bad.name]=='ERROR',ledger
    (ART/'migration_checks.json').write_text(json.dumps({'database':expected,'good':'OK','delayed_error':'ERROR','audit_error':'ERROR','rollback_values':values,'ledger':ledger},indent=2))
    print('Real SQL Server migration success, deferred error and rollback: PASS')
    engine.dispose()

if __name__=='__main__':main()
