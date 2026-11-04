import sys
import os
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'ETL'))
sys.path.insert(0, str(ROOT / 'backend'))
os.environ.setdefault('DB_SERVIDOR', 'offline-test')
os.environ.setdefault('DB_NOMBRE', 'offline-test')
os.environ.setdefault('ACP_JWT_SECRETO', 'offline-tests-only-do-not-use-in-production')

from tools import migration_runner as migrations
from utils.reproceso_atomico import reconstruir_fact_atomica
from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.errores import ErrorCircuitBreakerCritico, ErrorCircuitBreakerError
from servicios import servicio_proyecciones as service
from repositorios import repo_proyecciones as repo


def test_manifest_excludes_cleanup_and_unlisted_sql(tmp_path, monkeypatch):
    (tmp_path / 'manifest.json').write_text('{"migrations": ["safe.sql"]}')
    (tmp_path / 'safe.sql').write_text('SELECT 1')
    (tmp_path / 'new.sql').write_text('DELETE FROM important')
    monkeypatch.setattr(migrations, 'MIGRATIONS_DIR', tmp_path)
    assert [p.name for p in migrations._listar_migraciones_disponibles()] == ['safe.sql']
    (tmp_path / 'manifest.json').write_text('{"migrations": ["clear_all_data.sql"]}')
    with pytest.raises(ValueError): migrations._listar_migraciones_disponibles()


def test_repository_manifest_is_valid():
    names = [p.name for p in migrations._listar_migraciones_disponibles()]
    assert 'clear_all_data.sql' not in names
    assert 'fase71_habilitar_rcsi.sql' not in names
    assert 'fase70_consolidar_vistas_gold.sql' in names


@pytest.mark.parametrize('name', ['../escape.sql', 'sub/file.sql', 'sub\\file.sql', 'missing.sql'])
def test_manifest_rejects_invalid_paths(tmp_path, monkeypatch, name):
    import json
    (tmp_path / 'manifest.json').write_text(json.dumps({'migrations': [name]}))
    monkeypatch.setattr(migrations, 'MIGRATIONS_DIR', tmp_path)
    with pytest.raises(ValueError): migrations._listar_migraciones_disponibles()


def test_go_preserves_comments_strings_and_crlf():
    batches = migrations._separar_batches("-- header\r\nSELECT 'a\r\nGO\r\nb';\r\ngo -- next\r\n/*\r\nGO\r\n*/\r\nSELECT 2;\r\nGO")
    assert len(batches) == 2
    assert "SELECT 'a" in batches[0]
    assert 'SELECT 2' in batches[1]


def test_migration_failure_stops_dependents(monkeypatch):
    paths = [Path('a.sql'), Path('b.sql')]
    monkeypatch.setattr(migrations, '_listar_migraciones_disponibles', lambda: paths)
    monkeypatch.setattr(migrations, 'obtener_engine', Mock())
    monkeypatch.setattr(migrations, '_tabla_migraciones_existe', lambda e: True)
    monkeypatch.setattr(migrations, '_obtener_aplicadas', lambda e: {})
    monkeypatch.setattr(migrations, '_calcular_hash', lambda p: 'hash')
    apply = Mock(return_value={'estado': 'ERROR', 'error': 'failure', 'duracion': 0})
    monkeypatch.setattr(migrations, '_aplicar_migracion', apply)
    assert len(migrations.ejecutar()) == 1
    assert apply.call_count == 1


def test_migration_drift_blocks_execution(monkeypatch):
    monkeypatch.setattr(migrations, '_listar_migraciones_disponibles', lambda: [Path('a.sql')])
    monkeypatch.setattr(migrations, 'obtener_engine', Mock())
    monkeypatch.setattr(migrations, '_tabla_migraciones_existe', lambda e: True)
    monkeypatch.setattr(migrations, '_obtener_aplicadas', lambda e: {'a.sql': 'old'})
    monkeypatch.setattr(migrations, '_calcular_hash', lambda p: 'new')
    apply = Mock()
    monkeypatch.setattr(migrations, '_aplicar_migracion', apply)
    with pytest.raises(ValueError, match='modificada'): migrations.ejecutar()
    apply.assert_not_called()


@pytest.mark.parametrize('mode', ['exception', 'ERROR', 'CRITICO', 'empty', 'silent', 'ok'])
def test_rebuild_atomicity_with_real_transactions(tmp_path, mode):
    engine = create_engine('sqlite:///' + str(tmp_path / 'atomic.db'))
    with engine.begin() as con:
        con.execute(text('CREATE TABLE fact (value INTEGER)'))
        con.execute(text('CREATE TABLE bronze (state TEXT)'))
        con.execute(text('CREATE TABLE quarantine (reason TEXT)'))
        con.execute(text('INSERT INTO fact VALUES (7)'))
        con.execute(text("INSERT INTO bronze VALUES ('PROCESADO')"))
    def prepare(scoped):
        with scoped.begin() as con:
            con.execute(text('DELETE FROM fact'))
            con.execute(text("UPDATE bronze SET state='CARGADO'"))
        return {'filas_destino_eliminadas': 1}
    def load(scoped):
        with scoped.connect() as con:
            assert con.execute(text('SELECT COUNT(*) FROM fact')).scalar() == 0
        with ContextoTransaccionalETL(scoped) as context:
            con = context._conexion_activa()
            con.execute(text("INSERT INTO quarantine VALUES ('new')"))
            if mode != 'empty': con.execute(text('INSERT INTO fact VALUES (9)'))
            con.execute(text("UPDATE bronze SET state='PROCESADO_NUEVO'"))
        # Failure AFTER the inner loader context must still roll everything back.
        if mode == 'exception': raise RuntimeError('interrupted')
        return {'insertados': 0 if mode == 'empty' else 1,
                'breaker_nivel': mode if mode in ('ERROR', 'CRITICO') else None,
                'posible_perdida_silenciosa': mode == 'silent'}
    if mode == 'ok': reconstruir_fact_atomica(engine, prepare, load)
    else:
        with pytest.raises((RuntimeError, ErrorCircuitBreakerError, ErrorCircuitBreakerCritico)):
            reconstruir_fact_atomica(engine, prepare, load)
    with engine.connect() as con:
        assert con.execute(text('SELECT value FROM fact')).scalar() == (9 if mode == 'ok' else 7)
        assert con.execute(text('SELECT state FROM bronze')).scalar() == ('PROCESADO_NUEVO' if mode == 'ok' else 'PROCESADO')
        assert con.execute(text('SELECT COUNT(*) FROM quarantine')).scalar() == (1 if mode == 'ok' else 0)
    engine.dispose()


@pytest.mark.asyncio
async def test_projection_separates_fundos_and_keeps_ids(monkeypatch):
    counts = pd.DataFrame([
        dict(id_geografia=g, id_variedad=5, id_fundo=f, fundo=label, modulo=1, turno=1,
             valvula=1, variedad='V', condicion='C', certificacion='X', puntos=1,
             id_estado=9, total_organos=10)
        for g, f, label in [(101, 1, 'A'), (202, 2, 'B')]])
    plants = pd.DataFrame([dict(id_geografia=101, plantas_sampleadas=100, pct_productivas_s1=1),
                           dict(id_geografia=202, plantas_sampleadas=200, pct_productivas_s1=1)])
    weights = pd.DataFrame([dict(id_fundo=1, modulo=1, variedad='V', semana_iso=2, peso_baya_kg=.002),
                            dict(id_fundo=2, modulo=1, variedad='V', semana_iso=2, peso_baya_kg=.004)])
    monkeypatch.setattr(repo, 'extraer_datos_granulares', lambda *args: (counts, plants, weights))
    save = Mock(return_value={'insertados': 12, 'saltados': 0, 'errores': []})
    monkeypatch.setattr(repo, 'guardar_proyeccion', save)
    result = await service.ejecutar_proyeccion(20260101)
    detail = result['df_detalle']
    assert len(detail) == 12
    assert set(detail.id_geografia) == {101, 202}
    assert set(detail.id_variedad) == {5}
    assert result['kpis']['total_plantas'] == 300
    w1 = detail[detail.semana == 1].set_index('fundo')
    assert w1.loc['A', 'kg_base'] == .2
    assert w1.loc['B', 'kg_base'] == .8
    assert save.call_count == 1


def test_projection_persistence_uses_source_ids(monkeypatch):
    queries = []
    def query(sql, params):
        queries.append(sql)
        assert 'Dim_Geografia' not in sql
        return pd.DataFrame([{'ID_Tiempo': 20260108}])
    monkeypatch.setattr(repo, '_ejecutar_query_df', query)
    commands = Mock()
    monkeypatch.setattr(repo, '_ejecutar_comando', commands)
    detail = pd.DataFrame([dict(id_geografia=g, id_variedad=5, variedad='V', fecha_semana='2026-01-08',
                                kg_base=1, kg_pesimista=.9, kg_optimista=1.1) for g in [101, 202]])
    result = repo.guardar_proyeccion(detail, 20260101, .9, 1.1)
    assert result['insertados'] == 2
    assert [c.args[1]['id_g'] for c in commands.call_args_list] == [101, 202]


def test_projection_rejects_legacy_detail_without_ids(monkeypatch):
    command = Mock()
    monkeypatch.setattr(repo, '_ejecutar_comando', command)
    with pytest.raises(ValueError, match='IDs'):
        repo.guardar_proyeccion(pd.DataFrame([{'modulo': 1}]), 20260101, .9, 1.1)
    command.assert_not_called()

@pytest.mark.parametrize('failure', [False, True])
def test_pipeline_rerun_uses_atomic_boundary(tmp_path, monkeypatch, failure):
    import pipeline
    engine = create_engine('sqlite:///' + str(tmp_path / 'pipeline.db'))
    with engine.begin() as con:
        con.execute(text('CREATE TABLE fact (value INTEGER)'))
        con.execute(text('CREATE TABLE bronze (Estado_Carga TEXT)'))
        con.execute(text('INSERT INTO fact VALUES (7)'))
        con.execute(text("INSERT INTO bronze VALUES ('PROCESADO')"))
    def load(scoped):
        with scoped.connect() as con:
            assert con.execute(text('SELECT COUNT(*) FROM fact')).scalar() == 0
            assert con.execute(text('SELECT Estado_Carga FROM bronze')).scalar() == 'CARGADO'
        with ContextoTransaccionalETL(scoped) as context:
            context._conexion_activa().execute(text('INSERT INTO fact VALUES (9)'))
        if failure: raise RuntimeError('simulated loader failure')
        return {'leidos': 1, 'insertados': 1}
    monkeypatch.setattr(pipeline, 'obtener_engine', lambda: engine)
    monkeypatch.setattr(pipeline, 'verificar_conexion', lambda: True)
    monkeypatch.setattr(pipeline, 'limpiar_sesiones_huerfanas', lambda: None)
    monkeypatch.setattr(pipeline, '_obtener_contexto_sql', lambda e: {})
    monkeypatch.setattr(pipeline, 'limpiar_params', lambda: None)
    monkeypatch.setattr(pipeline, '_cargar_configuracion_operativa', lambda: {'facts_bloqueantes_gold': ['Test']})
    monkeypatch.setattr(pipeline, 'resolver_plan_reproceso', lambda **kw: {'facts': ['Test'], 'dependencias': [], 'marts': []})
    monkeypatch.setattr(pipeline, '_TABLAS_PERMITIDAS', {'fact', 'bronze'})
    monkeypatch.setattr(pipeline, 'CATALOGO_FACTS', {'Test': {'tabla_destino': 'fact', 'fuentes_bronce': ['bronze'], 'funcion': load}})
    monkeypatch.setattr(pipeline, 'registrar_inicio', lambda *a: 1)
    monkeypatch.setattr(pipeline, 'registrar_fin', lambda *a: None)
    if failure:
        with pytest.raises(pipeline.ErrorEjecucionPipeline): pipeline.ejecutar_reproceso_facts(['Test'])
    else: pipeline.ejecutar_reproceso_facts(['Test'])
    with engine.connect() as con:
        assert con.execute(text('SELECT value FROM fact')).scalar() == (7 if failure else 9)
        assert con.execute(text('SELECT Estado_Carga FROM bronze')).scalar() == ('PROCESADO' if failure else 'CARGADO')
    engine.dispose()


def test_extraction_preserves_geography_in_sql(monkeypatch):
    sqls = []
    def query(sql, params=None):
        sqls.append(sql)
        if 'sem_base' in sql: return pd.DataFrame([{'sem_base': 1, 'anio_base': 2026}])
        return pd.DataFrame()
    monkeypatch.setattr(repo, '_ejecutar_query_df', query)
    repo.extraer_datos_granulares(20260101)
    assert 'g.ID_Geografia AS id_geografia' in sqls[0]
    assert 'f.ID_Variedad AS id_variedad' in sqls[0]
    assert 'GROUP BY g.ID_Geografia' in sqls[0]
    assert 'g.ID_Geografia AS id_geografia' in sqls[1]
    for sql in sqls[3:]:
        assert 'g.ID_Fundo_Catalogo AS id_fundo' in sql
        assert 'GROUP BY g.ID_Fundo_Catalogo' in sql


@pytest.mark.asyncio
async def test_backend_openapi_liveness_and_projection_http(monkeypatch):
    import httpx
    from main import aplicacion
    from nucleo.auth import obtener_usuario_actual, UsuarioActual
    async def current_user():
        return UsuarioActual(nombre_usuario='offline', rol='admin', nombre_display='Offline')
    # No lifespan: avoids the real SQL Server readiness/background task.
    aplicacion.dependency_overrides[obtener_usuario_actual] = current_user
    async def calculate(**kwargs):
        return {'df_semanal': pd.DataFrame(), 'df_detalle': pd.DataFrame(), 'kpis': {}}
    monkeypatch.setattr(service, 'ejecutar_proyeccion', calculate)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=aplicacion), base_url='http://test') as client:
            assert (await client.get('/health/live')).status_code == 200
            schema = (await client.get('/openapi.json')).json()
            assert '/api/v1/proyecciones/ejecutar' in schema['paths']
            response = await client.post('/api/v1/proyecciones/ejecutar', json={'id_tiempo': 20260101})
            assert response.status_code == 200, response.text
            assert response.json()['df_semanal'] == []
    finally:
        aplicacion.dependency_overrides.clear()

@pytest.mark.parametrize('failure', [None, 'sql', 'audit'])
def test_migration_sql_and_success_audit_share_transaction(tmp_path, monkeypatch, failure):
    engine = create_engine('sqlite:///' + str(tmp_path / 'migration.db'))
    with engine.begin() as con:
        con.execute(text('CREATE TABLE data (value INTEGER)'))
        con.execute(text('CREATE TABLE audit (state TEXT)'))
    script = tmp_path / 'migration.sql'
    script.write_text('-- initial comment\nINSERT INTO data VALUES (1);\nGO\n' +
                      ('INVALID SQL;' if failure == 'sql' else '-- final comment\nINSERT INTO data VALUES (2);'))
    def record(con, path, sha, start, state, error):
        if state == 'OK' and failure == 'audit': raise RuntimeError('audit unavailable')
        con.execute(text('INSERT INTO audit VALUES (:state)'), {'state': state})
    monkeypatch.setattr(migrations, '_registrar_resultado', record)
    result = migrations._aplicar_migracion(engine, script, 'hash')
    assert result['estado'] == ('ERROR' if failure else 'OK')
    with engine.connect() as con:
        assert con.execute(text('SELECT COUNT(*) FROM data')).scalar() == (0 if failure else 2)
        assert con.execute(text('SELECT state FROM audit')).scalar() == result['estado']
    engine.dispose()

def test_odbc_deferred_error_is_not_ignored():
    from types import SimpleNamespace
    cursor=Mock()
    cursor.nextset.side_effect=[True,RuntimeError('SQLMoreResults error')]
    connection=SimpleNamespace(connection=SimpleNamespace(cursor=lambda:cursor))
    with pytest.raises(RuntimeError,match='SQLMoreResults'):
        migrations._ejecutar_batch(connection,'PRINT something;')
    cursor.close.assert_called_once()


def test_named_fundos_do_not_collapse_to_numbers(monkeypatch):
    from mdm import lookup
    lookup.limpiar_cache()
    frame=pd.DataFrame({'id':[1,2],'Fundo':['Fundo 2 Norte','Fundo 2 Sur']})
    monkeypatch.setattr(lookup,'_cargar_dim',lambda *args:frame)
    assert lookup._geo_nombre_token(' Fundo 2 Norte ')=='fundo 2 norte'
    assert lookup._obtener_id_catalogo(None,'test','id','Fundo','Fundo 2 Norte')==1
    assert lookup._obtener_id_catalogo(None,'test','id','Fundo','Fundo 2 Sur')==2
    assert lookup._obtener_id_catalogo(None,'test','id','Fundo','Unknown')==0
    lookup.limpiar_cache()


def test_ambiguous_geography_never_chooses_lowest_id(monkeypatch):
    from mdm import lookup
    monkeypatch.setattr(lookup,'_cargar_indice_geografia',lambda e:{(1,1,1,0):[
        {'ID_Geografia':1,'ID_Fundo_Catalogo':1,'ID_Sector_Catalogo':1},
        {'ID_Geografia':2,'ID_Fundo_Catalogo':2,'ID_Sector_Catalogo':2}]})
    result=lookup._resolver_id_geografia_desde_catalogos(None,0,0,1,1,1,0)
    assert result['id_geografia'] is None
    assert result['estado']=='GEOGRAFIA_AMBIGUA'


def test_unknown_fundo_never_falls_back_to_other_fundo(monkeypatch):
    from mdm import lookup
    lookup.limpiar_cache()
    monkeypatch.setattr(lookup,'_resolver_id_modulo_catalogo_con_reglas',lambda *args:(1,0))
    monkeypatch.setattr(lookup,'_obtener_id_catalogo',lambda *args:0 if args[3]=='Fundo' else 1)
    resolve=Mock()
    create=Mock()
    monkeypatch.setattr(lookup,'_resolver_id_geografia_desde_catalogos',resolve)
    monkeypatch.setattr(lookup,'_crear_combinacion_geografia',create)
    result=lookup.resolver_geografia('Unknown',None,1,None,turno=1,valvula=1)
    assert result['id_geografia'] is None
    resolve.assert_not_called()
    create.assert_not_called()
    lookup.limpiar_cache()
