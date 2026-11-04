---
type: design-spec
fecha: 2026-06-18
proyecto: ACP DWH — Documentación de cobertura total
estado: aprobado
tags: [documentacion, obsidian, etl, backend, portal, dwh]
---

# Spec — Documentación de cobertura total del sistema ACP DWH

## 1. Problema

El vault de Obsidian (`D:\Proyecto2026\.obsidian\ACP_DWH\Proyecciones`) es hoy un
**catálogo de datos**, no una documentación del sistema. Cubre bien la capa de base de
datos (99 tablas, 20 vistas, 14 SPs, ERD, conexiones, pipelines conceptuales) pero deja
sin documentar capas enteras y todo el "por qué":

- **Backend FastAPI:** 0 % en el vault (12 dominios de rutas, servicios, repositorios,
  `runner`, `nucleo` con auth/cache/rate_limit/event_bus).
- **Portal Next.js:** 0 % (19 páginas en 4 roles + 52 API routes, patrón BFF).
- **Internos del ETL:** solo mencionados, nunca explicados (`_base_processor`, dedup
  vectorizado, `circuit_breaker`, `contexto_transaccional`, `homologador`, cache MDM).
- **Capa compartida `comun/`** (conexion/sql_utils/validacion entre ETL y backend): no existe en el vault.
- **Transversales ausentes:** ADRs, catálogo de APIs, modelo RBAC, arquitectura del
  modelo de forecast/ML, flujo end-to-end, glosario de dominio.

### Problemas de calidad en lo ya escrito (bloqueantes)
- **Error fáctico:** `backend/README.md` dice que el backend lee de "SQLite optimizado".
  Es **SQL Server** (`DB_SERVIDOR`, `ODBC Driver 17 for SQL Server`, `comun/conexion.py`
  compartido con el ETL). SQLite solo se usa como *mock* en el perfil `test`.
- **Inconsistencia de idioma:** fichas con notas en inglés (p.ej.
  `tables/Gold.Mart_Proyecciones.md`) pese a que el vault declara "100 % español".
- **Columnas sin explicar:** columnas duplicadas/fantasma (`MAPE` NVARCHAR(MAX) vs
  `Error_MAPE` DECIMAL; `Fundo` texto vs `ID_Geografia`) listadas sin decir por qué existen
  (schema drift no documentado).

## 2. Objetivo y principio rector

**Objetivo del usuario:** cobertura total de las 3 capas, al nivel de calidad de la capa DB,
explicando de cada cosa **para qué sirve, por qué se hizo y por qué está ahí** — conciso,
3-4 líneas por unidad, no párrafos.

**Principio rector (del council):** la documentación es un *caché de conocimiento caro de
reconstruir*. El código ya documenta el *qué* y el *cómo* y nunca se desactualiza. Por tanto:

- La **amplitud** (cobertura total) se logra con **referencia autogenerada** (casi gratis).
- La **profundidad** (el "por qué") se escribe a mano **solo donde el código no la puede dar**.
- Cobertura total ≠ un archivo manual por cada uno de ~120 artefactos. Eso es un cementerio
  que se desincroniza en semanas (Opción A — descartada por unanimidad del council).

**Regla del "por qué":** todo "por qué" debe **nombrar el mal que se evita**, no la mecánica.
- ❌ "Por la restricción de VPD."
- ✅ "Para que la estimación de cosecha no se desvíe cuando sube la humedad."

## 3. Enfoque elegido

**Estructura de Opción B (narrativa por capa + deep-dives selectivos) con el motor de
Opción C (referencia autogenerada).** Veredicto del llm-council del 2026-06-18.

- Narrativa a **nivel de clúster**, no por artefacto: ~25 archivos manuscritos
  (3 capas + 12 dominios backend + 4 grupos de rol del portal), no 120.
- Cada unidad recibe sus 3-4 líneas de "por qué" en la **columna del catálogo**, no en su
  propio archivo.
- La referencia (endpoints, rutas, columnas) se **autogenera** y se valida contra la
  realidad mediante una compuerta.

## 4. Estructura destino del vault

```
Proyecciones/
├── 00_Start_Here.md           # NUEVO — puerta de entrada (qué es, quién usa, qué produce)
├── Glosario.md                # NUEVO — términos de dominio (campaña, VPD, GDD, fenología…)
├── Flujo_End_to_End.md        # NUEVO — un dato: Excel→Bronce→Silver→Gold→Backend→Portal
├── index.md                   # actualizar: enlazar nuevas secciones
├── tables/ views/ procedures/ # EXISTENTE — saneado en Fase 0
├── pipelines/                 # EXISTENTE
├── conexiones/                # EXISTENTE
├── comun/                     # NUEVO — capa compartida ETL+backend
│   └── index.md               #   (conexion, sql_utils, validacion)
├── backend/                   # NUEVO
│   ├── index.md               #   overview + diagrama + arranque local
│   ├── Catalogo_API.md        #   AUTOGENERADO desde /openapi.json + columna "por qué"
│   ├── nucleo.md              #   auth, cache, rate_limit, middleware, event_bus, settings
│   ├── runner.md              #   ejecutor del ETL desde el backend
│   └── dominios/              #   1 archivo por dominio de ruta (12)
│       ├── auth.md  alertas.md  analista.md  auditoria.md  catalogos.md
│       ├── config.md  cuarentena.md  etl.md  health.md  ingesta.md
│       └── proyecciones.md  reinyeccion.md
├── portal/                    # NUEVO
│   ├── index.md               #   overview + patrón BFF + arquitectura de carpetas
│   ├── Catalogo_Rutas.md      #   AUTOGENERADO desde el filesystem (page.tsx + route.ts)
│   └── roles/                 #   1 archivo por grupo de rol (4)
│       ├── admin.md  analyst.md  executive.md  auth.md
├── seguridad/                 # NUEVO
│   └── RBAC.md                #   roles, JWT, rate-limiting, flujo de login, Seguridad.Usuarios
├── modelo_forecast/           # NUEVO — el "core" del negocio
│   └── Arquitectura_Forecast.md  # lógica del modelo, supuestos, escenarios, MAPE/override
└── decisiones/                # NUEVO en vault (enlaza docs/decisiones/ del repo)
    └── ADR-*.md               #   por qué medallion, circuit breaker 5 %, snowflake, BFF
```

## 5. Formato de cada unidad

**Archivo de clúster (narrativa por capa/dominio/rol):**
```markdown
# <Nombre del clúster>

## Qué es
<1-2 líneas: qué responsabilidad cubre este clúster.>

## Por qué existe
<1-2 líneas nombrando el mal que evita.>

## Cómo se usa / De qué depende
<1-2 líneas: entradas, salidas, módulos de los que depende.>

## Catálogo
| Unidad | Método/Ruta | Qué hace | Por qué (mal que evita) | Depende de |
|--------|-------------|----------|-------------------------|------------|
```

**Catálogo autogenerado (`Catalogo_API.md`, `Catalogo_Rutas.md`):** tabla con columnas de
referencia (método, ruta, schema de entrada/salida, auth) generadas por script + una columna
**"Por qué"** rellenada a mano. El script **nunca** sobrescribe la columna "Por qué".

## 6. Fases (orden de ejecución)

### Fase 0 — Saneamiento (BLOQUEANTE, primero)
- [ ] Corregir `backend/README.md`: "SQLite" → SQL Server (SQLite solo en perfil `test`).
- [ ] Fijar español como idioma canónico; traducir fichas con notas en inglés
      (empezar por `tables/Gold.Mart_Proyecciones.md` y barrer el resto).
- [ ] Documentar o marcar como deuda las columnas-fantasma (`MAPE`/`Error_MAPE`,
      `Fundo`/`ID_Geografia`, etc.) en sus fichas.

### Fase 1 — Puerta de entrada
- [ ] `00_Start_Here.md` (qué es el sistema, quién lo usa, qué produce, a dónde ir).
- [ ] `Glosario.md` (campaña, condición de cultivo, fenología, VPD, GDD, jerarquía
      Fundo→Sector→Módulo→Turno→Válvula→Cama, escenario de proyección…).
- [ ] `Flujo_End_to_End.md` (diagrama de un dato de punta a punta).

### Fase 2 — Referencia autogenerada (probar en 3 endpoints primero)
- [ ] Script que vuelca `/openapi.json` → `backend/Catalogo_API.md`.
- [ ] Script que camina el filesystem del portal (`page.tsx` + `route.ts`) → `portal/Catalogo_Rutas.md`.
- [ ] **Validar en 3 endpoints reales** que el OpenAPI emite schemas limpios antes de
      generar todo; si emite basura, corregir tipado o ajustar el generador.

### Fase 3 — Narrativa "por qué" por clúster (~25 archivos)
- [ ] `backend/index.md` + `nucleo.md` + `runner.md` + 12 archivos de dominio.
- [ ] `portal/index.md` + 4 archivos de rol.
- [ ] `comun/index.md`.

### Fase 4 — El "core" y las decisiones
- [ ] `modelo_forecast/Arquitectura_Forecast.md` (lógica, supuestos, escenarios, MAPE, override).
- [ ] `seguridad/RBAC.md` (roles, JWT, rate-limiting, login, `Seguridad.Usuarios`).
- [ ] ADRs en `decisiones/` (por qué medallion, circuit breaker 5 %, snowflake, BFF) —
      partiendo de los 2 ADRs ya existentes en `docs/decisiones/` del repo.

### Fase 5 (transversal) — Compuerta de verificación
- [ ] Check que falle si un endpoint/tabla documentado ya no existe (compara contra
      `/openapi.json` vivo y el schema de la DB) o si hay drift de idioma.
- [ ] Enganchar la regeneración de catálogos a `graphify update` / pre-commit para que la
      referencia no se pudra.

## 7. Qué NO se hace (YAGNI)
- ❌ Una ficha manual por endpoint/página/servicio (Opción A).
- ❌ Documentar el *qué/cómo* que el código ya expresa (firmas triviales, getters/setters).
- ❌ Tratar las 99 fichas DB actuales como el estándar de calidad: están defectuosas
      (idioma, columnas sin explicar). La barra se **redefine**, no se copia.

## 8. Riesgos
- **OpenAPI sucio:** si los modelos de respuesta están a medio tipar o las rutas BFF no
  están en ningún schema, el generador produce basura → mitigado por la prueba de 3 endpoints
  en Fase 2.
- **Staleness:** docs que se desincronizan del código → mitigado por la compuerta de Fase 5.
- **Sobre-alcance:** "cobertura total" derivando en boilerplate inmantenible → mitigado por
  la regla de narrativa a nivel de clúster + referencia autogenerada.

## 9. Criterio de éxito
Un dev (o un agente LLM) puede hacer un cambio correcto en cualquiera de las 3 capas
**sin spelunking del código fuente**, y ninguna página del vault contiene una afirmación
falsa verificable.
