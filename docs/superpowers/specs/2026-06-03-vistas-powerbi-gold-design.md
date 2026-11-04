# Spec — Vistas legibles `PowerBI.*` sobre Gold para Power BI

**Fecha:** 2026-06-03
**Autor:** brainstorming colaborativo (carlo + agente)
**Base de datos:** `ACP_DataWarehose_Proyecciones` (SQL Server, server `.`, Windows Auth)

---

## 1. Problema

Power BI consume directamente las tablas `Gold.Mart_*`. Esas tablas exponen
llaves crudas (`ID_Tiempo`, `ID_Campana`, `ID_Geografia`, `ID_Variedad`,
`ID_Escenario`, `ID_Estado_Fenologico`, `ID_Cinta`, `ID_Personal`,
`ID_Actividad`). En Power BI se ven como números sin significado:

- `ID_Tiempo = 20250516` no se interpreta como fecha.
- `ID_Campana = 3` no dice "Campaña 2026".

El usuario final no sabe que `20250516` es una fecha → reportes confusos.

## 2. Objetivo

Crear una capa de **vistas desnormalizadas y 100% legibles** que Power BI
consuma en lugar de las tablas. Cada vista **reemplaza los IDs de lookup por
sus columnas de texto/fecha** resolviendo los joins a las dimensiones.

## 3. Decisiones de diseño (aprobadas)

1. **Reemplazar IDs por nombres** — las vistas NO exponen columnas `ID_*` de
   lookup. (Se conserva únicamente la PK surrogate del Mart, ej.
   `ID_Mart_Cosecha`, como llave única de fila para Power BI.)
2. **Alcance: los 13 Marts** de `Gold`.
3. **Esquema nuevo `PowerBI`** — solo vistas; `Gold` queda con tablas físicas.
4. **Geografía con detalle completo** — resolver `ID_Geografia` a toda la
   jerarquía: Fundo, Sector, Modulo, SubModulo, Tipo_Conduccion, Turno,
   Valvula, Cama, Codigo_SAP_Campo.

## 4. Reglas transversales

- **`LEFT JOIN` siempre** — nunca perder filas del Mart por un ID nulo/0.
- **`COALESCE` para etiquetas** — `ID_Campana = 0` → `'SIN_CAMPAÑA'`;
  geografía no encontrada → `'(sin asignar)'`.
- **`Fecha` como tipo `date` real** (desde `Dim_Tiempo.Fecha`) — clave para
  que Power BI la trate como fecha, no como entero.
- **Orden de columnas**: PK surrogate → dimensiones descriptivas
  (Fecha/Anio/Mes/Nombre_Mes/Semana_ISO → Nombre_Campana → jerarquía
  geográfica → Variedad → resto de catálogos) → métricas → Fecha_Actualizacion.
- **`CREATE OR ALTER VIEW`** — idempotente, re-ejecutable sin drops.
- Cuando un Mart ya trae una columna de texto redundante con el join
  (ej. `Fundo`, `Modulo`, `Variedad`), **se usa la versión resuelta desde la
  dimensión** como fuente única y se descarta la redundante del Mart.

## 5. Tabla de resolución de IDs

| ID crudo | Reemplazo legible | Dimensión |
|---|---|---|
| `ID_Tiempo` | `Fecha` (date), `Anio`, `Mes`, `Nombre_Mes`, `Semana_ISO` | `Silver.Dim_Tiempo` |
| `ID_Campana` | `Nombre_Campana` | `Silver.Dim_Campana` |
| `ID_Geografia` | `Fundo`, `Sector`, `Modulo`, `SubModulo`, `Tipo_Conduccion`, `Turno`, `Valvula`, `Cama`, `Codigo_SAP_Campo`, `Nivel_Granularidad` | `Silver.Dim_Geografia` + 6 catálogos |
| `ID_Variedad` | `Variedad`, `Breeder` | `Silver.Dim_Variedad` |
| `ID_Escenario` | `Tipo_Escenario`, `Descripcion_Escenario` | `Silver.Dim_Escenario_Proyeccion` |
| `ID_Estado_Fenologico` | `Estado_Fenologico` | `Silver.Dim_Estado_Fenologico` |
| `ID_Cinta` | `Color_Cinta` | `Silver.Dim_Cinta` |
| `ID_Personal` | `Nombre_Personal`, `DNI`, `Rol` | `Silver.Dim_Personal` |
| `ID_Actividad` | `Nombre_Actividad`, `Nombre_Labor`, `Categoria` | `Silver.Dim_Actividad_Operativa` |

### Join de geografía completo
`Mart.ID_Geografia = Dim_Geografia.ID_Geografia`, y desde `Dim_Geografia`:
- `ID_Fundo_Catalogo → Dim_Fundo_Catalogo.Fundo`
- `ID_Sector_Catalogo → Dim_Sector_Catalogo.Sector`
- `ID_Modulo_Catalogo → Dim_Modulo_Catalogo.Modulo, SubModulo, Tipo_Conduccion`
- `ID_Turno_Catalogo → Dim_Turno_Catalogo.Turno`
- `ID_Valvula_Catalogo → Dim_Valvula_Catalogo.Valvula`
- `ID_Cama_Catalogo → Dim_Cama_Catalogo.Cama_Normalizada` (alias `Cama`)
- columnas propias: `Codigo_SAP_Campo`, `Nivel_Granularidad`

## 6. Mapa por Mart (joins requeridos)

| Vista | Tiempo | Campaña | Geografía | Variedad | Otros joins | Notas |
|---|:--:|:--:|:--:|:--:|---|---|
| `vw_Cosecha` | ✔ | ✔ | ✔ | ✔ | — | trae `Fecha_Cosecha` (date), `Turno`, `Condicion` propios |
| `vw_Proyecciones` | ✔ | ✔ | ✔ | ✔ | `ID_Escenario` | trae `Estado_Workflow`, `Version_*`, fechas propias |
| `vw_Censo_Plantas` | ✔ | ✔ | ✔ | ✔ | — | `Estado_Planta`, `Cantidad` propios |
| `vw_Ciclo_Poda` | ✔ | ✔ | ✔ | ✔ | — | métricas de poda |
| `vw_Evaluacion_Vegetativa` | ✔ | ✔ | ✔ | ✔ | — | `Piso` propio |
| `vw_Fisiologia` | ✔ | ✔ | ✔ | ✔ | — | `Tercio` propio |
| `vw_Induccion_Floral` | ✔ | ✔ | ✔ | ✔ | — | `Tipo_Evaluacion` propio |
| `vw_Tasa_Crecimiento` | ✔ | ✔ | ✔ | ✔ | — | `Estado_Vegetativo`, `Tipo_Tallo` |
| `vw_Pesos_Calibres` | ✔ | ✔ | ✔ | ✔ | — | `Evaluador`, `Estado_DQ` propios |
| `vw_Maduracion` | ✔ | ✔ | ✔ | ✔ | `ID_Estado_Fenologico`, `ID_Cinta` | (Mart vacío hoy) |
| `vw_Administrativo` | ✔ | ✔ | ✖ | ✖ | `ID_Personal`, `ID_Actividad` | sin geografía/variedad; ya trae texto de personal/actividad (Mart vacío hoy) |
| `vw_Clima` | ✔ | ✔ | ✖ | ✖ | — | usa `Sector_Climatico` (texto, sin `ID_Geografia`) |
| `vw_Fenologia` | ✖ | ✖ | ✖ | ✖ | — | **sin IDs de lookup**: solo `Semana_ISO`, `Modulo`, `Variedad`, `Color_Cinta`, `Estado_Fenologico` ya en texto → vista de puro renombre/orden |

**Marts vacíos hoy** (0 filas): `Mart_Administrativo`, `Mart_Maduracion`,
`Mart_Proyecciones`. Se crean igual; funcionarán cuando el ETL los llene.

## 7. Entregable

1. Script SQL idempotente en
   `ETL/sql_migrations/fase20_vistas_powerbi.sql`:
   - `CREATE SCHEMA PowerBI` (si no existe).
   - `CREATE OR ALTER VIEW PowerBI.vw_*` × 13.
2. Script de verificación (Python sobre `.venv`) que confirma:
   - las 13 vistas existen y son consultables;
   - cada vista con Mart no vacío devuelve `COUNT(*)` igual al del Mart base
     (los `LEFT JOIN` no inflan ni reducen filas);
   - ninguna vista expone columnas que empiecen con `ID_` salvo la PK
     surrogate `ID_Mart_*`.

## 8. Fuera de alcance (YAGNI)

- No se modela un esquema estrella en Power BI (el usuario eligió vistas
  planas legibles).
- No se tocan las tablas `Gold.Mart_*` ni el ETL que las puebla.
- No se crean medidas DAX ni el .pbix.
