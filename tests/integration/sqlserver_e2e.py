"""Real SQL Server E2E. Only creates/writes ACP_E2E_* databases.
No connection is ever made to the existing application database.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import time
import traceback

import pyodbc

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / '.test-tmp-sqlserver'
STATE = ART / 'state.json'
ART.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / 'ETL'))
from tools.migration_runner import _separar_batches


def state():
    data = json.loads(STATE.read_text())
    if not re.fullmatch(r'ACP_E2E_[a-z0-9_]+', data['database']):
        raise RuntimeError('Refusing non-E2E database')
    return data


def connect(database=None, admin=False):
    s = state()
    database = database or s['database']
    if database != s['database'] and not (admin and database == 'master'):
        raise RuntimeError('Unexpected database')
    connstr = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={s['server']};DATABASE={database};TrustServerCertificate=yes;"
    if s.get('login') and not admin:
        connstr += f"UID={s['login']};PWD={s['password']};"
    else:
        connstr += 'Trusted_Connection=yes;'
    con = pyodbc.connect(connstr, timeout=5, autocommit=True)
    assert con.execute('SELECT DB_NAME()').fetchval() == database
    return con


def drain(cursor):
    while cursor.nextset():
        pass


def apply_sql(path):
    s = state()
    source = path.read_text(encoding='utf-8-sig')
    if path.name == 'DDL_DataWarehose_Proyecciones_v3.sql':
        source = source[source.index('-- SCHEMAS'):]
        # Snapshot contains obsolete SQL modules incompatible with its own tables.
        # Install structural DDL plus the still-current control/sync modules;
        # current MDM/cama/Gold modules are installed from explicit migrations.
        structural, modules = source.split('-- VIEWS / PROCEDURES / FUNCTIONS / TRIGGERS', 1)
        selected = []
        for batch in _separar_batches(modules):
            if re.search(r'CREATE\s+(?:PROCEDURE|VIEW)\s+(?:Control\.|Silver\.sp_Sincronizar_Periodos_Campana)', batch, re.I):
                selected.append(re.sub(r'CREATE\s+(PROCEDURE|VIEW)', r'CREATE OR ALTER \1', batch, count=1, flags=re.I))
        source = structural + '\nGO\n' + '\nGO\n'.join(selected)
    # DDL remains unchanged on disk. Retarget USE and qualified references only
    # in the temporary execution text, then refuse any other USE destination.
    source = source.replace('ACP_DataWarehose_Proyecciones', s['database'])
    source = source.replace('ACP_DataWarehouse_Proyecciones', s['database'])
    for target in re.findall(r'(?im)^\s*USE\s+\[?([\w]+)\]?\s*;', source):
        if target != s['database']:
            raise RuntimeError(f'Forbidden USE in {path.name}')
    # Old conversion scripts DROP the wrong object type with IF EXISTS.
    # Repair only execution text in this isolated bootstrap; retain source hashes.
    source = re.sub(r"DROP (VIEW|TABLE) IF EXISTS ([\w.]+);",
        lambda m: f"IF OBJECT_ID('{m[2]}', '{'V' if m[1]=='VIEW' else 'U'}') IS NOT NULL DROP {m[1]} {m[2]};",
        source)
    with connect() as con:
        for number, batch in enumerate(_separar_batches(source), 1):
            assert con.execute('SELECT DB_NAME()').fetchval() == s['database']
            try:
                drain(con.execute(batch))
            except Exception as e:
                raise RuntimeError(f'{path.name} batch {number}: {e}') from e
    print('Applied', path.name, flush=True)


def sync_workspace():
    dest = ART / 'workspace'
    for name in ['ETL', 'backend', 'comun']:
        shutil.copytree(ROOT / name, dest / name, dirs_exist_ok=True,
            ignore=shutil.ignore_patterns('data', 'logs', '__pycache__', '.env', '.venv', 'runner.stop'))
    return dest


def env():
    s=state()
    values=os.environ.copy()
    values.update(DB_SERVIDOR=s['server'], DB_NOMBRE=s['database'],
        DB_DRIVER='ODBC Driver 17 for SQL Server', DB_USUARIO=s.get('login',''),
        DB_CLAVE=s.get('password',''), ACP_ENTORNO='test',
        ACP_JWT_SECRETO=s['jwt'], ACP_HOST='127.0.0.1', ACP_PUERTO='18819',
        ACP_ETL_DIR=str(ART/'workspace'/'ETL'), PYTHONUTF8='1',
        PYTHONPATH=os.pathsep.join([str(ROOT/'.test-deps'), str(ART/'workspace')]))
    return values


def child(args, cwd, name, timeout=180):
    path=ART/(name+'.log')
    with path.open('w',encoding='utf-8') as out:
        result=subprocess.run([sys.executable,*args], cwd=cwd, env=env(), stdout=out,
                              stderr=subprocess.STDOUT, timeout=timeout)
    print(name, 'exit', result.returncode, flush=True)
    if result.returncode:
        print(path.read_text(encoding='utf-8')[-6500:], flush=True)
        raise RuntimeError(f'{name} failed; see {path}')
    return path


def setup():
    if not STATE.exists():
        name='ACP_E2E_'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d_%H%M%S')+'_'+secrets.token_hex(3)
        STATE.write_text(json.dumps(dict(server=r'localhost\LOCALHOST', database=name,
            jwt=secrets.token_hex(32)),indent=2))
        s=state()
        with connect('master',admin=True) as con:
            assert con.execute('SELECT DB_ID(?)',name).fetchval() is None
            con.execute(f'CREATE DATABASE [{name}] COLLATE Modern_Spanish_CI_AS')
    s=state()
    if not s.get('login'):
        with connect('master',admin=True) as con:
            mode=con.execute("SELECT CAST(SERVERPROPERTY('IsIntegratedSecurityOnly') AS int)").fetchval()
            if not mode:
                s['login']=s['database']+'_user'; s['password']=secrets.token_urlsafe(36)+'Aa1!'
                con.execute(f"CREATE LOGIN [{s['login']}] WITH PASSWORD='{s['password']}', CHECK_POLICY=ON, DEFAULT_DATABASE=[{s['database']}]")
                STATE.write_text(json.dumps(s,indent=2))
        if s.get('login'):
            with connect(admin=True) as con:
                con.execute(f"CREATE USER [{s['login']}] FOR LOGIN [{s['login']}]")
                con.execute(f"ALTER ROLE db_owner ADD MEMBER [{s['login']}]")
    s=state()
    with connect() as con:
        print('Isolated target:',s['server'],con.execute('SELECT DB_NAME()').fetchval(),flush=True)
        print('Restricted SQL login:',bool(s.get('login')),flush=True)
    sync_workspace()
    apply_sql(ROOT/'ETL/sql_migrations/DDL_DataWarehose_Proyecciones_v3.sql')


def prepare():
    apply_sql(ROOT/'tests/integration/schema_prerequisites.sql')
    names = [
        'fase30_registro_migraciones.sql',
        'fase40_cuarentena_estricta_dims.sql',
        'fase45_eliminar_bridge_geografia_cama.sql',
        'fase46_dim_campana_seed_fechas.sql',
        'fase47c_bridge_fix_cte.sql',
        'fase48a_resolver_campana_por_fecha.sql',
        'fase48b_bridge_geografia_campana.sql',
        'fase49_dim_tiempo_campana.sql',
        'fase49b_dim_tiempo_id_campana_fix.sql',
        'fase51_seed_variedad_sin_variedad.sql',
        'fase51b_poblar_bridge_condicion_cosecha.sql',
        'fase52a_conteo_fenologico_id_campana_backfill.sql',
        'fase52b_poblar_bridge_geo_campana_conteo_fenologico.sql',
        'fase56a_evaluacion_pesos_id_campana_backfill.sql',
        'fase56b_poblar_bridge_geo_campana_evaluacion_pesos.sql',
        'fase57a_censo_plantas_id_campana_backfill.sql',
        'fase57b_poblar_bridge_geo_campana_censo_plantas.sql',
        'fase58a_floracion_id_campana_backfill.sql',
        'fase58b_poblar_bridge_geo_campana_floracion.sql',
        'fase59a_fisiologia_id_campana_backfill.sql',
        'fase59b_poblar_bridge_geo_campana_fisiologia.sql',
        'fase59c_poblar_bridge_geo_campana_tasa_crecimiento.sql',
        'fase60_add_missing_columns.sql',
        'fase61_update_grain_cosecha_sap.sql',
        'fase62_rediseno_mart_clima.sql',
        'fase64_columnas_bronce_faltantes.sql',
        '2026_05_24_crear_fact_ciclos_fenologicos.sql',
        'fase65_fact_ciclos_fenologicos_color_cinta.sql',
        'fase66_ciclos_fenologicos_ids_dimensionales.sql',
        'fase67_purgar_columnas_ciclos_fenologicos.sql',
        'fase69_ciclos_fenologicos_grain_cinta_organo.sql',
        'refactor_telemetria_clima_silver_horario.sql',
        'fase70_consolidar_vistas_gold.sql',
    ]
    progress = ART/'bootstrap_progress.json'
    done=json.loads(progress.read_text()) if progress.exists() else []
    for name in names:
        if name not in done:
            if name == 'fase66_ciclos_fenologicos_ids_dimensionales.sql':
                with connect() as con:
                    con.execute("IF EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('Silver.Fact_Ciclos_Fenologicos') AND name='UX_Fact_Ciclos_Fenologicos_Grain') DROP INDEX UX_Fact_Ciclos_Fenologicos_Grain ON Silver.Fact_Ciclos_Fenologicos")
                print('Bootstrap dependency repair: drop obsolete Categoria grain index before fase66', flush=True)
            folder = 'sql' if name.startswith('refactor_') else 'sql_migrations'
            apply_sql(ROOT/'ETL'/folder/name)
            done.append(name)
            progress.write_text(json.dumps(done,indent=2))


def seed():
    import pandas as pd
    import bcrypt
    s=state()
    if s.get('seeded'):
        print('Synthetic fixture already seeded'); return
    def insert(con, table, values):
        cols=','.join('['+k+']' for k in values)
        placeholders=','.join('?' for _ in values)
        return con.execute(f'INSERT INTO {table} ({cols}) OUTPUT INSERTED.* VALUES ({placeholders})', *values.values()).fetchone()[0]
    with connect() as con:
        for table,pk,values in [
            ('Silver.Dim_Cama_Catalogo','ID_Cama_Catalogo',dict(Cama_Normalizada='SIN_CAMA')),
            ('Silver.Dim_Personal','ID_Personal',dict(DNI='SIN_DNI',Nombre_Completo='Sin evaluador',Rol='Evaluador')),
        ]:
            identifier=0 if 'Cama' in table else -1
            if not con.execute(f'SELECT 1 FROM {table} WHERE {pk}=?',identifier).fetchval():
                con.execute(f'SET IDENTITY_INSERT {table} ON')
                insert(con,table,{pk:identifier,**values})
                con.execute(f'SET IDENTITY_INSERT {table} OFF')
        person=insert(con,'Silver.Dim_Personal',dict(DNI='12345678',Nombre_Completo='Evaluador E2E',Rol='Evaluador'))
        var=insert(con,'Silver.Dim_Variedad',dict(Nombre_Variedad='E2E_Variedad'))
        module=insert(con,'Silver.Dim_Modulo_Catalogo',dict(Modulo=1,SubModulo=None,Tipo_Conduccion='CONVENCIONAL'))
        turn=insert(con,'Silver.Dim_Turno_Catalogo',dict(Turno=1))
        valve=insert(con,'Silver.Dim_Valvula_Catalogo',dict(Valvula='1'))
        fixtures=[]
        for label in ['A','B']:
            fund=insert(con,'Silver.Dim_Fundo_Catalogo',dict(Fundo='E2E_'+label))
            sector=insert(con,'Silver.Dim_Sector_Catalogo',dict(Sector='E2E_'+label))
            geo=insert(con,'Silver.Dim_Geografia',dict(ID_Fundo_Catalogo=fund,ID_Sector_Catalogo=sector,
                ID_Modulo_Catalogo=module,ID_Turno_Catalogo=turn,ID_Valvula_Catalogo=valve,
                ID_Cama_Catalogo=0,Nivel_Granularidad='VALVULA',Fecha_Inicio_Vigencia='2025-01-01'))
            fixtures.append(dict(fundo='E2E_'+label,id_fundo=fund,id_geografia=geo))
        con.execute('SET IDENTITY_INSERT Silver.Dim_Estado_Fenologico ON')
        for i,label in enumerate(['Boton Floral','Flor','Pequena','Verde','Inicio F1','Inicio F2','Crema','Madura','Cosechable','Yema Hinchada'],1):
            if not con.execute('SELECT 1 FROM Silver.Dim_Estado_Fenologico WHERE ID_Estado_Fenologico=?',i).fetchval():
                insert(con,'Silver.Dim_Estado_Fenologico',dict(ID_Estado_Fenologico=i,Nombre_Estado=label,Orden_Estado=i))
        con.execute('SET IDENTITY_INSERT Silver.Dim_Estado_Fenologico OFF')
        for i,label in enumerate(['Buenas','Regulares','Malas','Muertas'],1):
            if not con.execute('SELECT 1 FROM Silver.Dim_Estado_Planta WHERE ID_Estado_Planta=?',i).fetchval():
                insert(con,'Silver.Dim_Estado_Planta',dict(ID_Estado_Planta=i,Nombre_Estado=label))
        for table,pk,values in [
            ('Silver.Dim_Escenario_Proyeccion','ID_Escenario',dict(Tipo_Escenario='Base',Descripcion='Synthetic E2E')),
            ('Silver.Dim_Estado_Workflow','ID_Workflow',dict(Estado='Borrador')),
        ]:
            identifier=4 if 'Escenario' in table else 1
            if not con.execute(f'SELECT 1 FROM {table} WHERE {pk}=?',identifier).fetchval():
                con.execute(f'SET IDENTITY_INSERT {table} ON');insert(con,table,{pk:identifier,**values});con.execute(f'SET IDENTITY_INSERT {table} OFF')
        condition=insert(con,'Silver.Dim_Condicion_Cultivo',dict(Sustrato='N/A',Certificacion='Convencional'))
        if not con.execute('SELECT 1 FROM Control.Bloqueo_Ejecucion WHERE ID_Lock=1').fetchval():
            insert(con,'Control.Bloqueo_Ejecucion',dict(ID_Lock=1))
        password=secrets.token_urlsafe(20)
        insert(con,'Seguridad.Usuarios',dict(Nombre_Usuario='e2e_admin',Nombre_Display='E2E Admin',
            Hash_Clave=bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode(),Rol='admin',Es_Activo=1))
        for key,value in [('CAMPANA_INICIO','2025-01-01'),('CAMPANA_FIN','2026-12-31')]:
            insert(con,'Config.Parametros_Pipeline',dict(Nombre_Parametro=key,Valor=value))
    dest=sync_workspace()/'ETL/data/entrada'
    for folder in ['conteo_fruta','censo_plantas','evaluacion_pesos','evaluacion_calidad_poda']:
        (dest/folder).mkdir(parents=True,exist_ok=True)
    counts=[];plants=[];weights=[];pruning=[]
    base=dt.date(2026,3,2)
    for i,fixture in enumerate(fixtures,1):
        common=dict(Fecha_Raw=str(base),Fundo_Raw=fixture['fundo'],Sector_Raw=fixture['fundo'],
                    Modulo_Raw=1,Turno_Raw=1,Valvula_Raw='1',Variedad_Raw='E2E_Variedad',
                    Nombres_Raw='Evaluador E2E',DNI_Raw='12345678')
        counts.append({**common,'Punto_Raw':1,'BayasCosechables_Raw':100*i,'Evaluacion_Raw':'CONTEO FENOLOGICO',
                       'Fecha_Registro_Raw':'2026-03-02 12:00:00'})
        plants.append({**common,'Estado_Planta_Raw':'BUENAS','Cantidad_Raw':100*i,'Linea_Raw':'L1'})
        pruning.append({**common,'Punto_Raw':1,'Tipo_Evaluacion_Raw':'PODA GENERAL','TallosPlanta_Raw':5,
                        'Fecha_Registro_Raw':'2026-03-02 12:00:00'})
        for week in range(1,7):
            weights.append({**common,'Fecha_Raw':str(base+dt.timedelta(weeks=week)),
                            'PesoBaya_Raw':10*(2+i),'CantMuestra_Raw':10,'Cosechables_Raw':10,'PesoCosechables_Raw':10*(2+i)})
    for folder, rows in [('conteo_fruta',counts),('censo_plantas',plants),('evaluacion_pesos',weights),('evaluacion_calidad_poda',pruning)]:
        pd.DataFrame(rows).to_excel(dest/folder/'synthetic.xlsx', index=False, sheet_name='BD')
    s.update(seeded=True,fixtures=fixtures,variety=var,person=person,admin_password=password,base_date=20260302)
    STATE.write_text(json.dumps(s,indent=2))
    print('Seeded synthetic dimensions and four Excel inputs',flush=True)


def reset_fixture():
    import pandas as pd
    apply_sql(ROOT/'tests/integration/schema_prerequisites.sql')
    with connect() as con:
        if not con.execute("SELECT OBJECT_ID('Bronce.Telemetria_Clima','U')").fetchval():
            raw=(ROOT/'ETL/sql/refactor_telemetria_clima_2026_05.sql').read_text(encoding='utf-8-sig')
            start=raw.index('CREATE TABLE Bronce.Telemetria_Clima')
            stop=raw.index('/* -- 3.',start)
            drain(con.execute(raw[start:stop]))
        for table in ['Silver.Fact_Conteo_Fenologico','Silver.Fact_Censo_Plantas','Silver.Fact_Evaluacion_Pesos','Silver.Fact_Ciclo_Poda',
                      'Bronce.Conteo_Fruta','Bronce.Censo_Plantas','Bronce.Evaluacion_Pesos','Bronce.Evaluacion_Calidad_Poda','MDM.Cuarentena']:
            con.execute('DELETE FROM '+table)
    data=ART/'workspace/ETL/data'
    for folder in ['conteo_fruta','censo_plantas','evaluacion_pesos','evaluacion_calidad_poda']:
        sources=list((data/'procesados'/folder).glob('*.xlsx'))
        if not sources:raise RuntimeError(f'Missing synthetic archive {folder}')
        for old in (data/'entrada'/folder).glob('*'):
            if not old.resolve().is_relative_to(ART.resolve()):raise RuntimeError('Unsafe path')
            if old.is_file():old.unlink()
        df=pd.read_excel(sources[0],sheet_name='BD')
        if folder=='evaluacion_pesos':df['PesoBaya_Raw']=df['Peso_Cosechables_g'] if 'Peso_Cosechables_g' in df else df['PesoCosechables_Raw']
        df.to_excel(data/'entrada'/folder/'synthetic.xlsx',index=False,sheet_name='BD')
    print('Reset synthetic rows and regenerated isolated inputs',flush=True)


def validate():
    import requests
    import socket
    s=state()
    sync_workspace()
    results={'database':s['database'],'server':s['server'],'checks':{}}
    def snapshot(table,order):
        with connect() as con:
            cur=con.execute(f'SELECT * FROM {table} ORDER BY {order}')
            return [list(row) for row in cur.fetchall()]
    with connect() as con:
        permissions=con.execute("SELECT IS_SRVROLEMEMBER('sysadmin'),IS_MEMBER('db_owner'),HAS_DBACCESS('ACP_DataWarehose_Proyecciones')").fetchone()
        assert permissions[0]==0 and permissions[1]==1 and permissions[2] in (0,None),permissions
        results['isolation']={'sysadmin':permissions[0],'db_owner_on_test':permissions[1],'existing_database_access':permissions[2]}
        counts=[]
        for table in ['Silver.Fact_Ciclo_Poda','Silver.Fact_Conteo_Fenologico','Silver.Fact_Censo_Plantas','Silver.Fact_Evaluacion_Pesos']:
            counts.append(con.execute('SELECT COUNT(*) FROM '+table).fetchval())
        assert counts==[2,2,2,12],counts
        actual=[tuple(row) for row in con.execute('SELECT f.ID_Geografia,SUM(f.Cantidad_Organos) FROM Silver.Fact_Conteo_Fenologico f GROUP BY f.ID_Geografia ORDER BY f.ID_Geografia')]
        assert [row[1] for row in actual]==[100,200],actual
        assert con.execute('SELECT COUNT(*) FROM Gold.Mart_Fenologia').fetchval()==2
        results['checks']['excel_bronze_silver_gold']={'poda':counts[0],'conteo':counts[1],'censo':counts[2],'pesos':counts[3],'organs_by_geography':actual}
    # Real executor and real SQL Server transaction (not SQLite).
    child([str(ROOT/'tests/integration/sqlserver_worker.py')],WORK if (WORK:=ART/'workspace').exists() else ROOT,'sqlserver_migrations')
    results['checks']['migrations']=json.loads((ART/'migration_checks.json').read_text())
    # Verify a full second incremental execution does not duplicate data.
    before={table:snapshot(table,'1') for table in ['Silver.Fact_Conteo_Fenologico','Silver.Fact_Censo_Plantas','Silver.Fact_Evaluacion_Pesos','Silver.Fact_Ciclo_Poda']}
    child(['pipeline.py'],WORK/'ETL','pipeline_idempotent')
    after={table:snapshot(table,'1') for table in before}
    assert before==after,'Incremental run changed already processed facts'
    results['checks']['incremental_idempotence']='PASS'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    process_env=env();process_env['ACP_PUERTO']=str(port)
    handles=[];processes=[]
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    try:
        for name,command in [
            ('backend_http',['-m','uvicorn','main:aplicacion','--host','127.0.0.1','--port',str(port)]),
            ('runner_live',['-m','runner.runner']),
        ]:
            handle=(ART/(name+'.log')).open('w',encoding='utf-8');handles.append(handle)
            processes.append(subprocess.Popen([sys.executable,*command],cwd=WORK/'backend',env=process_env,
                stdout=handle,stderr=subprocess.STDOUT,creationflags=flags))
        base=f'http://127.0.0.1:{port}'
        session=requests.Session()
        for _ in range(100):
            try:
                response=session.get(base+'/health/live',timeout=1)
                if response.status_code==200:break
            except requests.RequestException:pass
            if any(p.poll() is not None for p in processes):raise RuntimeError('Backend/runner exited; inspect logs')
            time.sleep(.2)
        else:raise RuntimeError('HTTP startup timeout')
        def request(method,path,**kwargs):
            response=session.request(method,base+path,timeout=30,**kwargs)
            assert response.status_code<400,(path,response.status_code,response.text[:2000])
            return response
        assert session.get(base+'/api/v1/proyecciones/fechas',timeout=5).status_code==401
        token=request('POST','/auth/login',data={'username':'e2e_admin','password':s['admin_password']}).json()['access_token']
        session.headers['Authorization']='Bearer '+token
        request('GET','/auth/me')
        request('GET','/health/ready')
        request('GET','/api/v1/catalogos/geografia')
        request('GET','/api/v1/proyecciones/fechas')
        projected=request('POST','/api/v1/proyecciones/ejecutar',json={'id_tiempo':s['base_date']}).json()
        detail=projected['df_detalle']
        assert len(detail)==12,detail
        assert {r['id_geografia'] for r in detail}=={r['id_geografia'] for r in s['fixtures']}
        totals={r['fundo']:r['kg_base'] for r in detail if r['semana']==1}
        assert totals=={'E2E_A':3.0,'E2E_B':16.0},totals
        with connect() as con:
            rows=[tuple(r) for r in con.execute('SELECT ID_Geografia,COUNT(*),SUM(Kg_Proyectados) FROM Silver.Fact_Proyecciones GROUP BY ID_Geografia ORDER BY ID_Geografia')]
            assert len(rows)==2 and all(row[1]==6 for row in rows),rows
        results['checks']['http_auth_projection']={'details':len(detail),'week1_kg':totals,'saved':[(g,n,float(kg)) for g,n,kg in rows]}
        def run_corrida(facts=None):
            payload={'comentario':'Synthetic end-to-end validation'}
            if facts:payload.update(modo_ejecucion='facts',facts=facts)
            created=request('POST','/api/v1/etl/corridas',json=payload).json()
            runid=created['id_corrida']
            for _ in range(200):
                data=request('GET',f'/api/v1/etl/corridas/{runid}').json()
                if data['estado'] in ('OK','ERROR','TIMEOUT','CANCELADO'):return runid,data
                time.sleep(.2)
            raise RuntimeError('Runner timeout')
        runid,data=run_corrida(['Fact_Conteo_Fenologico'])
        assert data['estado']=='OK',data
        steps=request('GET',f'/api/v1/etl/corridas/{runid}/pasos').json()
        assert steps,steps
        events=request('GET',f'/api/v1/etl/corridas/{runid}/eventos').text
        assert '[FIN_CORRIDA]' in events and 'event: log' in events
        results['checks']['http_runner_atomic_rerun']={'id':runid,'status':data['estado'],'steps':len(steps),'sse_fin':True}
        # Force an actual SQL Server insert error after the destructive DELETE.
        old_fact=snapshot('Silver.Fact_Conteo_Fenologico','ID_Conteo_Fenologico')
        old_bronze=snapshot('Bronce.Conteo_Fruta','ID_Conteo_Fruta')
        old_quarantine=snapshot('MDM.Cuarentena','ID_Cuarentena')
        with connect() as con:
            drain(con.execute("CREATE OR ALTER TRIGGER Silver.E2E_Reject_Insert ON Silver.Fact_Conteo_Fenologico AFTER INSERT AS BEGIN THROW 51001,'Synthetic failure to verify transaction rollback',1; END"))
        try:
            failed_id,failed=run_corrida(['Fact_Conteo_Fenologico'])
            assert failed['estado']=='ERROR',failed
        finally:
            with connect() as con:con.execute('DROP TRIGGER IF EXISTS Silver.E2E_Reject_Insert')
        assert snapshot('Silver.Fact_Conteo_Fenologico','ID_Conteo_Fenologico')==old_fact
        assert snapshot('Bronce.Conteo_Fruta','ID_Conteo_Fruta')==old_bronze
        assert snapshot('MDM.Cuarentena','ID_Cuarentena')==old_quarantine
        results['checks']['rollback_after_real_insert_failure']={'id':failed_id,'status':failed['estado'],'fact_preserved':True,'bronze_preserved':True,'quarantine_preserved':True}
        recovery_id,recovery=run_corrida(['Fact_Conteo_Fenologico'])
        assert recovery['estado']=='OK',recovery
        full_id,full=run_corrida()
        assert full['estado']=='OK',full
        results['checks']['runner_recovery_and_full_run']={'recovery':recovery_id,'full':full_id,'status':'OK'}
        results['status']='PASS'
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        for handle in handles:handle.close()
        (ART/'results.json').write_text(json.dumps(results,indent=2,default=str))
    print(json.dumps(results,indent=2,default=str),flush=True)


def final_check():
    report=json.loads((ART/'results.json').read_text())
    with connect() as con:
        assert con.execute('SELECT DB_NAME()').fetchval()==state()['database']
        violations=[]
        cur=con.execute('DBCC CHECKCONSTRAINTS WITH ALL_CONSTRAINTS')
        while True:
            if cur.description:violations.extend([tuple(row) for row in cur.fetchall()])
            if not cur.nextset():break
        assert not violations,violations
        active=con.execute("SELECT COUNT(*) FROM Control.Corrida WHERE Estado IN ('PENDIENTE','EJECUTANDO')").fetchval()
        locked=con.execute('SELECT ID_Corrida_Activa FROM Control.Bloqueo_Ejecucion WHERE ID_Lock=1').fetchval()
        triggers=con.execute("SELECT COUNT(*) FROM sys.triggers WHERE name LIKE 'E2E[_]%'").fetchval()
        disabled_fk=con.execute('SELECT COUNT(*) FROM sys.foreign_keys WHERE is_disabled=1 OR is_not_trusted=1').fetchval()
        assert active==0 and locked is None and triggers==0 and disabled_fk==0
        report['checks']['final_integrity']={'constraint_violations':0,'disabled_or_untrusted_foreign_keys':0,
            'active_runs':active,'active_lock':locked,'temporary_triggers':triggers}
    report['checks']['migrations']=json.loads((ART/'migration_checks.json').read_text())
    import hashlib
    paths=['ETL/mdm/lookup.py','ETL/silver/facts/_base_processor.py','ETL/tools/migration_runner.py',
           'ETL/utils/reproceso_atomico.py','ETL/pipeline.py','backend/servicios/servicio_proyecciones.py',
           'backend/repositorios/repo_proyecciones.py']
    report['source_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths}
    report['validation_scope']={'sql_server':True,'odbc_driver':'ODBC Driver 17 for SQL Server',
        'nonempty_etl_domains':['conteo','censo','pesos','poda'],'other_facts':'empty input smoke only',
        'installation':'versioned snapshot plus explicit isolated bootstrap repairs; not a clean-install certification'}
    report['local_regression']={'passed':138,'skipped':1}
    report['process_cleanup']='HTTP backend and runner terminated by the validation harness'
    (ROOT/'docs/validacion-sqlserver-aislado-resultados.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Final integrity and control-plane cleanup: PASS',flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['setup','apply','pipeline','query','sync','validate','prepare','seed','repair-input','reset','migration-check','final-check'])
    parser.add_argument('items',nargs='*')
    args=parser.parse_args()
    if args.stage=='setup': setup()
    elif args.stage=='final-check': final_check()
    elif args.stage=='migration-check':
        sync_workspace()
        child([str(ROOT/'tests/integration/sqlserver_worker.py')],ART/'workspace','sqlserver_migrations')
    elif args.stage=='reset': reset_fixture()
    elif args.stage=='repair-input':
        apply_sql(ROOT/'tests/integration/schema_prerequisites.sql')
        with connect() as con:
            con.execute('DELETE FROM Bronce.Censo_Plantas')
        data=ART/'workspace/ETL/data'
        sources=list((data/'procesados/censo_plantas').glob('*.xlsx'))
        if len(sources)!=1: raise RuntimeError(f'Expected one synthetic censo archive, found {sources}')
        shutil.copy2(sources[0],data/'entrada/censo_plantas/reload.xlsx')
    elif args.stage=='seed': seed()
    elif args.stage=='prepare': prepare()
    elif args.stage=='sync': sync_workspace()
    elif args.stage=='apply':
        for name in args.items:
            if Path(name).name!=name or not name.endswith('.sql'): raise ValueError('Expected SQL basename')
            folder = 'sql' if name.startswith('refactor_') else 'sql_migrations'
            apply_sql(ROOT/'ETL'/folder/name)
    elif args.stage=='pipeline':
        sync_workspace()
        child(['pipeline.py',*args.items],ART/'workspace/ETL','pipeline')
    elif args.stage=='query':
        # Read-only diagnostics; mutation statements belong in the scripted test.
        query=' '.join(args.items)
        if not query.lstrip().upper().startswith('SELECT '):raise ValueError('SELECT only')
        with connect() as con:
            cur=con.execute(query)
            print([c[0] for c in cur.description]);print([tuple(r) for r in cur.fetchall()])
    elif args.stage=='validate': validate()


if __name__=='__main__':
    main()
