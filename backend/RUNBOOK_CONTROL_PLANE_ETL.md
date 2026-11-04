# Runbook Control Plane ETL

## Alcance

Este runbook cubre la operación diaria del backend ETL, el runner y el esquema `Control.*` en `ACP_DataWarehose_Proyecciones`.

Aplica a:
- API FastAPI
- runner separado
- ETL monolítico con `pipeline.py`
- corridas completas y `rerun` dirigido por fact

## Prerrequisitos

- Backend operativo con `.venv`
- Runner levantado en proceso separado
- Esquema `Control.*` creado
- Script [fase21_endurecimiento_control_plane.sql](D:\Proyecto2026\ACP_DWH\ACP%20Proyecciones\ETL\fase21_endurecimiento_control_plane.sql) ejecutado
- Script [fase22_retencion_control_plane.sql](D:\Proyecto2026\ACP_DWH\ACP%20Proyecciones\ETL\fase22_retencion_control_plane.sql) ejecutado

## Chequeo diario de 5 minutos

### 1. Validar salud HTTP

PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
Invoke-RestMethod http://127.0.0.1:8000/health/ready/control
Invoke-RestMethod http://127.0.0.1:8000/health/ready/runner
Invoke-RestMethod http://127.0.0.1:8000/health/lock
```

Esperado:
- `/health/live`: `estado = vivo`
- `/health/ready`: `estado = listo`
- `/health/ready/control`: `estado = listo`
- `/health/ready/runner`: `estado = libre` o `ocupado`
- `/health/lock`: `estado = libre` o `activo`

### 1.1 Validar catálogo y trazabilidad ETL

Con token `viewer+`:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/etl/facts -Headers @{ Authorization = 'Bearer <TOKEN>' }
Invoke-RestMethod http://127.0.0.1:8000/api/v1/etl/corridas/<ID_CORRIDA> -Headers @{ Authorization = 'Bearer <TOKEN>' }
Invoke-RestMethod http://127.0.0.1:8000/api/v1/etl/corridas/<ID_CORRIDA>/pasos -Headers @{ Authorization = 'Bearer <TOKEN>' }
```

Esperado:
- `/facts` devuelve solo facts soportadas por `rerun`
- `/corridas/{id}` devuelve parametros ETL decodificados y `pasos`
- `/corridas/{id}/pasos` devuelve la secuencia realmente ejecutada

### 2. Validar cola y corridas activas

SQL:

```sql
SELECT * FROM Control.vw_Corridas_Activas;
SELECT * FROM Control.vw_Cola_Comandos ORDER BY ID_Comando DESC;
SELECT * FROM Control.vw_Ultima_Corrida_Por_Tabla ORDER BY Fecha_Inicio DESC;
```

Esperado:
- sin crecimiento anómalo de comandos `PENDIENTE`
- sin lock vencido
- sin corridas activas huérfanas

### 3. Ejecutar ETL

Completo:

```powershell
Set-Location 'D:\Proyecto2026\ACP_DWH\ACP Proyecciones'
.\ejecutar_etl_acp.bat
```

Rerun clima:

```powershell
Set-Location 'D:\Proyecto2026\ACP_DWH\ACP Proyecciones'
.\ejecutar_etl_acp.bat --modo-ejecucion facts --facts Fact_Telemetria_Clima
```

Rerun múltiple:

```powershell
Set-Location 'D:\Proyecto2026\ACP_DWH\ACP Proyecciones'
.\ejecutar_etl_acp.bat --modo-ejecucion facts --facts Fact_Evaluacion_Pesos Fact_Tareo
```

## Incidentes comunes

### 1. `lock_vencido`

Síntoma:
- `/health/ready/runner` responde `lock_vencido`

Diagnóstico:

```sql
SELECT * FROM Control.Bloqueo_Ejecucion;
SELECT * FROM Control.vw_Corridas_Activas;
```

Acción:
1. Confirmar que no exista un `python.exe` real ejecutando `runner.py` o `pipeline.py`.
2. Si no existe proceso vivo, liberar el lock manualmente:

```sql
UPDATE Control.Bloqueo_Ejecucion
SET ID_Corrida_Activa = NULL,
    Adquirido_Por = NULL,
    Fecha_Adquisicion = NULL,
    Heartbeat = NULL
WHERE ID_Lock = 1;
```

3. Reiniciar runner.
4. Revalidar `/health/ready/runner`.

### 2. Comandos `PENDIENTE` no avanzan

Síntoma:
- `Control.Comando_Ejecucion` acumula comandos `PENDIENTE`

Diagnóstico:

```sql
SELECT * FROM Control.vw_Cola_Comandos ORDER BY ID_Comando DESC;
SELECT * FROM Control.Bloqueo_Ejecucion;
```

Acción:
1. Verificar que el runner esté levantado.
2. Si el lock está libre y la cola no avanza, reiniciar runner.
3. Si el lock está activo pero sin heartbeat reciente, tratar como `lock_vencido`.

### 3. Corrida `ERROR` o `TIMEOUT`

Diagnóstico:

```sql
SELECT *
FROM Control.Corrida
WHERE ID_Corrida = '<ID_CORRIDA>';

SELECT TOP (200) *
FROM Control.Corrida_Evento
WHERE ID_Corrida = '<ID_CORRIDA>'
ORDER BY ID_Evento DESC;

SELECT *
FROM Control.Corrida_Paso
WHERE ID_Corrida = '<ID_CORRIDA>'
ORDER BY Orden, ID_Paso;
```

Acción:
1. Identificar si el fallo fue de SQL, DQ o parser.
2. Si el daño es localizado, usar `rerun` dirigido.
3. Si el fallo afecta carga base o varias facts, correr ETL completo.

### 4. Cancelación operativa

Preferir API:

```powershell
Invoke-RestMethod -Method Delete http://127.0.0.1:8000/api/v1/etl/corridas/<ID_CORRIDA> -Headers @{ Authorization = 'Bearer <TOKEN>' }
```

Validar:

```sql
SELECT ID_Corrida, Estado, Fecha_Fin, Mensaje_Final
FROM Control.Corrida
WHERE ID_Corrida = '<ID_CORRIDA>';
```

## Mantenimiento control-plane

### Aplicar endurecimiento SQL

Orden:
1. [crear_tablas_control.sql](D:\Proyecto2026\ACP_DWH\ACP%20Proyecciones\ETL\crear_tablas_control.sql)
2. [fase21_endurecimiento_control_plane.sql](D:\Proyecto2026\ACP_DWH\ACP%20Proyecciones\ETL\fase21_endurecimiento_control_plane.sql)
3. [fase22_retencion_control_plane.sql](D:\Proyecto2026\ACP_DWH\ACP%20Proyecciones\ETL\fase22_retencion_control_plane.sql)

### Purga operativa del historial

Ejecucion manual:

```sql
EXEC Control.sp_Purgar_Historial_Control;
```

Ejecucion con parametros explicitos:

```sql
EXEC Control.sp_Purgar_Historial_Control
    @Retencion_Dias_Corrida = 365,
    @Retencion_Dias_Evento = 90,
    @Retencion_Dias_Comando = 180;
```

Reglas:

- nunca purga corridas activas
- solo purga corridas cerradas (`OK`, `ERROR`, `CANCELADO`, `TIMEOUT`)
- purga primero eventos/comandos/pasos y luego corridas elegibles

### Verificación posterior

```sql
SELECT name
FROM sys.indexes
WHERE object_id IN (
    OBJECT_ID('Control.Corrida'),
    OBJECT_ID('Control.Corrida_Evento'),
    OBJECT_ID('Control.Corrida_Paso'),
    OBJECT_ID('Control.Comando_Ejecucion')
)
ORDER BY object_id, name;

SELECT OBJECT_NAME(object_id) AS Vista
FROM sys.views
WHERE SCHEMA_NAME(schema_id) = 'Control'
ORDER BY Vista;

EXEC Control.sp_Purgar_Historial_Control
    @Retencion_Dias_Corrida = 365,
    @Retencion_Dias_Evento = 90,
    @Retencion_Dias_Comando = 180;
```

## Criterios de operación sana

- No hay comandos `PENDIENTE` envejecidos sin explicación
- No hay `lock_vencido`
- Las corridas `EJECUTANDO` tienen heartbeat reciente
- El ETL parcial se usa para correcciones focalizadas
- El ETL completo se reserva para cargas del día o correcciones amplias
- La traza de `Control.Corrida_Paso` coincide con el resumen operativo del pipeline
- El catálogo `/api/v1/etl/facts` coincide con el manifiesto interno del ETL
