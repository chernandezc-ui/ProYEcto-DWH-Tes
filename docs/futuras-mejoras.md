# Futuras mejoras a aplicar — ACP DWH

**Fecha del análisis:** 2026-06-17
**Alcance:** Portal Next.js + Backend FastAPI + ETL Pipeline + Cross-cutting
**Estado:** Catálogo de oportunidades. Ningún item ejecutado todavía; este documento es la fuente para priorizar trabajo futuro.

## Cómo leer este documento

Cada item tiene:
- **Esfuerzo:** S (≤1 día), M (1–3 días), L (>3 días o semanas)
- **Impacto:** 🔥 alto crítico · alto · medio · bajo
- Razón corta (qué problema resuelve)
- Notas técnicas cuando aplican

Los items están agrupados por capa:
- [A. Portal Next.js](#a-portal-nextjs)
- [B. Backend FastAPI](#b-backend-fastapi)
- [C. ETL Pipeline](#c-etl-pipeline)
- [D. Cross-cutting (DB / Deploy / DX / Observability)](#d-cross-cutting-db--deploy--dx--observability)
- [Recomendación — Top 5 ROI](#recomendación--top-5-roi-para-aplicar-primero)
- [Lo que NO recomiendo atacar ahora](#lo-que-no-recomiendo-atacar-ahora)

---

## A. Portal Next.js

### A.1 Performance / Bundle

#### A.1.1 Migrar de Plotly a Recharts donde aplique
- **Esfuerzo:** M
- **Impacto:** 🔥 alto
- **Razón:** Plotly pesa ~4.5MB en chunks lazy. Los gráficos del portal son tipos básicos (bar, line, pie, area). Recharts cubre el caso con ~150KB y ya está como dependencia.
- **Acción:** Auditar qué visualizaciones realmente requieren Plotly (3D, mapas, anotaciones complejas). El resto migrar a Recharts.
- **Side effect bueno:** permite quitar `'unsafe-eval'` de CSP, mejora seguridad.

#### A.1.2 `useSuspenseQuery` en zonas críticas del dashboard
- **Esfuerzo:** M
- **Impacto:** medio
- **Razón:** Hoy la cache hidratada vía `HydrationBoundary` elimina la mayoría del flash, pero en race conditions (prefetch slow → mount fast) puede mostrarse skeleton antes que datos. Suspense-native lo elimina.
- **Cuidado:** incompatible con `keepPreviousData`. Migrar hook por hook midiendo regresión.

#### A.1.3 Virtualizar `<DwhLineageGraph>` si tiene >50 nodos visibles
- **Esfuerzo:** M
- **Impacto:** medio (si aplica)
- **Razón:** Fue split de 1231 líneas. Probablemente render-heavy con muchos nodos. Sin profiling real no se justifica; medir primero con DevTools.

#### A.1.4 React Compiler (RC en Next 16)
- **Esfuerzo:** S configurar
- **Impacto:** alto si funciona
- **Razón:** Automatiza la memoización que hoy escribimos a mano con `useMemo`/`useCallback`. Riesgo: el compiler está en RC, puede tener edge cases en hooks complejos.
- **Acción:** activar con flag opt-in primero en pantallas no críticas.

#### A.1.5 Preact en producción
- **Esfuerzo:** M
- **Impacto:** medio
- **Razón:** Drop-in replacement, ~10KB vs 45KB de React. Trade-off: pierde features experimentales y soporte de algunos libraries con React-internals.
- **Recomendación:** NO atacar ahora. Riesgo alto por edge cases.

---

### A.2 Arquitectura / Calidad de código

#### A.2.1 Adoptar el endpoints layer en hooks existentes
- **Esfuerzo:** L
- **Impacto:** alto a futuro
- **Razón:** `lib/api/endpoints.ts` ya existe (commit `0e876a7`) con `defineEndpoint()`/`callEndpoint()`. Solo `quality.ts` lo usa de ejemplo. Migrar los 30+ hooks restantes elimina drift cliente/server.
- **Adopción:** gradual, hook por hook al tocarlos. No migración masiva.

#### A.2.2 `useBaseMutation` propagado a las mutaciones existentes
- **Esfuerzo:** M
- **Impacto:** medio
- **Razón:** `hooks/mutations/use-base-mutation.ts` (commit `e1da5f5`) propone toast + invalidación consistente. Hoy hay 7 mutaciones con boilerplate duplicado.

#### A.2.3 Query-keys factory consumido en todos los `invalidateQueries`
- **Esfuerzo:** M
- **Impacto:** medio
- **Razón:** `lib/query-keys.ts` existe con factory tipada. Hoy los `invalidateQueries` usan strings mágicos. Migración elimina typos.

#### A.2.4 i18n estructural con `next-intl`
- **Esfuerzo:** L
- **Impacto:** bajo hoy
- **Razón:** Hoy todo es español hardcoded. Solo justificado si hay roadmap real de internacionalización.

#### A.2.5 Storybook para componentes UI
- **Esfuerzo:** L
- **Impacto:** medio DX
- **Razón:** 50+ componentes UI sin documentación visual. Storybook facilita audit visual + testing aislado. Habilita Chromatic/Percy para visual regression.

#### A.2.6 Middleware RBAC consolidado
- **Esfuerzo:** M
- **Impacto:** medio (riesgo alto)
- **Razón:** Hoy la lógica de roles vive en layouts y `requireRole` por ruta. Un `middleware.ts` único centraliza el control y reduce drift.
- **Cuidado:** toca el auth flow. Requiere brainstorm dedicado + tests e2e antes.

---

### A.3 Diseño / UX

#### A.3.1 Tabs con URL state
- **Esfuerzo:** S
- **Impacto:** alto UX
- **Razón:** `hooks/use-url-state.ts` ya existe. Aplicarlo a todas las pantallas con tabs hace que refresh y deep-link funcionen (ej. mandar link `/catalogos?tab=geografia&sector=Norte`).

#### A.3.2 Skeleton-first hydration
- **Esfuerzo:** M
- **Impacto:** medio
- **Razón:** Patrón `loading={query.isLoading && !query.data}` está repetido en cada componente. Suspense lo elimina y centraliza la lógica.

#### A.3.3 Sistema de breadcrumbs
- **Esfuerzo:** S
- **Impacto:** medio
- **Razón:** El sidebar muestra la sección pero no contexto del subpath actual (ej. `/etl-monitor/[id]` solo dice "Monitor ETL", no qué corrida).

#### A.3.4 Atajos de teclado globales
- **Esfuerzo:** M
- **Impacto:** alto DX
- **Razón:** Hay ⌘K palette ya. Faltan atajos secuenciales tipo `g d` (dashboard), `g q` (quality), `g c` (catálogos). Reduce mouse-dependency para power users.

#### A.3.5 Modo offline-friendly
- **Esfuerzo:** L
- **Impacto:** medio
- **Razón:** Service Worker que cachea last-known dashboard data. Útil para usuarios con conexión inestable. Feature nueva grande.

#### A.3.6 Empty states ilustrados consistentes
- **Esfuerzo:** S
- **Impacto:** medio
- **Razón:** `<EmptyState>` ya existe. Asegurar uso uniforme en cada tabla/listado vacío en vez de `<p>Sin datos</p>` ad-hoc.

---

### A.4 Testing

#### A.4.1 Vitest + MSW para tests de hooks
- **Esfuerzo:** M
- **Impacto:** alto
- **Razón:** Cero tests unitarios hoy. Hooks como `useQuality`, `useGeografia`, `useEntities` tienen lógica de paginación + filtros que deberían cubrirse. MSW para mock del backend.

#### A.4.2 Playwright golden paths completos
- **Esfuerzo:** M
- **Impacto:** alto
- **Razón:** Hay smoke tests pero falta journey completo. Ej.: login → resolver cuarentena → ver el cambio reflejado en dashboard.

#### A.4.3 Chromatic / Percy
- **Esfuerzo:** M
- **Impacto:** medio
- **Razón:** Visual regression automático. Requiere Storybook previamente (A.2.5).

---

## B. Backend FastAPI

### B.1 Performance / Escalabilidad

#### B.1.1 Reemplazar `pyodbc` por `aioodbc` o equivalente async
- **Esfuerzo:** L
- **Impacto:** alto en carga
- **Razón:** Hoy las queries pasan por `asyncio.to_thread`, lo que serializa la concurrencia real. `aioodbc` (o `asyncpg` si la BD lo soporta) hace queries nativamente async, libera workers para más requests concurrentes.

#### B.1.2 Connection pooling explícito
- **Esfuerzo:** S
- **Impacto:** alto si hay timeouts
- **Razón:** Verificar que SQLAlchemy use `pool_pre_ping=True` y `pool_recycle` razonable (~30 min). SQL Server cierra conexiones idle agresivamente y `pre_ping` evita errores "MARS connection broken".

#### B.1.3 Cache Redis en vez de SQLite local
- **Esfuerzo:** M
- **Impacto:** alto si escala
- **Razón:** `backend/cache_portal.db` es SQLite — single-writer, no funciona con múltiples workers. Redis es multi-worker safe + TTL nativo + pub/sub para invalidación cross-worker.

#### B.1.4 Múltiples workers de uvicorn
- **Esfuerzo:** S
- **Impacto:** alto en throughput
- **Razón:** El comando actual `uvicorn main:aplicacion` es single-worker por default. En producción usar `--workers N` o `gunicorn -k uvicorn.workers.UvicornWorker -w N`. Bloqueado hasta que B.1.3 esté hecho (SQLite cache no funciona con N workers).

#### B.1.5 HTTP/2 + gzip compression
- **Esfuerzo:** S
- **Impacto:** medio
- **Razón:** `gzip` middleware está en FastAPI; verificar si está activo. HTTP/2 requiere reverse proxy (nginx, Caddy) — verificar si está delante de uvicorn.

---

### B.2 Estructura / Calidad de código

#### B.2.1 Cleanup de scratch en producción
- **Esfuerzo:** S
- **Impacto:** bajo (limpieza)
- **Razón:** `backend/scratch/`, `scratch_list_users.py`, `scratch_test_decode.py` no deberían estar en el repo. Mover a `.gitignore` o eliminar.

#### B.2.2 OpenAPI tipado + `openapi-typescript`
- **Esfuerzo:** M
- **Impacto:** alto (cierra drift)
- **Razón:** FastAPI ya emite OpenAPI. Agregar Pydantic v2 con tags + descriptions completos. El cliente Next puede auto-generar tipos TypeScript con `openapi-typescript`, eliminando el drift Zod cliente vs Pydantic server.

#### B.2.3 Migrations con Alembic
- **Esfuerzo:** M (si falta)
- **Impacto:** alto
- **Razón:** Existe `backend/migrations/`. Verificar si está cableado con Alembic. Sin migrations versionadas, los cambios de schema son manuales y propensos a drift entre ambientes.

#### B.2.4 Rate limiting aplicado
- **Esfuerzo:** S
- **Impacto:** alto security
- **Razón:** `backend/nucleo/rate_limit.py` existe. Verificar que esté aplicado al menos a endpoints públicos (login, register, password reset). Sin rate limit hay riesgo de brute force.

#### B.2.5 Logging estructurado con `structlog`
- **Esfuerzo:** M
- **Impacto:** alto observability
- **Razón:** `nucleo/logging.py` ya existe. Verificar que emita JSON estructurado con correlation IDs (un request_id que viaja por todos los logs del mismo request). Habilita observability decente cross-stack.

#### B.2.6 Health check enriquecido
- **Esfuerzo:** S
- **Impacto:** medio
- **Razón:** Separar `/health/live` (proceso responde) de `/health/ready` (DB + cache reachable). Patrón estándar de Kubernetes. Permite restart automático cuando el proceso vive pero la DB cayó.

---

### B.3 Tests / Calidad

#### B.3.1 Tests pytest para endpoints restantes
- **Esfuerzo:** L
- **Impacto:** alto
- **Razón:** Hoy solo geografía tiene tests (commit `165c91e`, 8/8 verdes). Faltan: quality, catalogos restantes, ETL, auth. El scaffolding ya existe en `backend/tests/conftest.py`.

#### B.3.2 CI con pytest + lint
- **Esfuerzo:** M
- **Impacto:** alto
- **Razón:** No hay `.github/workflows/`. Sin CI, los tests no garantizan nada en PR. Patrón mínimo: GitHub Actions que corre `pytest`, `eslint`, `tsc`, `playwright` en cada PR.

#### B.3.3 Type checking del backend
- **Esfuerzo:** M
- **Impacto:** medio
- **Razón:** `mypy --strict` o `pyright` sobre el backend. Hoy probablemente tipos parciales. Cierra una clase entera de bugs en runtime.

---

### B.4 Seguridad

#### B.4.1 Audit log de mutaciones MDM
- **Esfuerzo:** M
- **Impacto:** alto compliance
- **Razón:** Quién resolvió/descartó cada registro de cuarentena, quién creó cada variedad, quién cambió cada catálogo. Tabla `MDM.AuditLog` con FK al usuario.

#### B.4.2 Rotación corta de JWT + refresh token silencioso
- **Esfuerzo:** M
- **Impacto:** alto security
- **Razón:** Hoy probablemente JWT vive 24h fijo. Reducir a 1h con refresh token silencioso reduce ventana de exposición si un token se filtra.

#### B.4.3 CSP sin `'unsafe-eval'`
- **Esfuerzo:** M
- **Impacto:** alto security
- **Razón:** El `unsafe-eval` actual existe porque Plotly lo requiere. Si A.1.1 (migrar parcial a Recharts) avanza, se puede aplicar CSP estricto en las rutas que ya no lo necesitan.

#### B.4.4 Secrets management
- **Esfuerzo:** M
- **Impacto:** alto
- **Razón:** `.env` en disco está bien para dev. Para producción, mover a Vault, AWS Secrets Manager, Azure Key Vault, etc. Sin esto, los secretos viajan en backups y logs.

---

## C. ETL Pipeline

### C.1 Arquitectura

#### C.1.1 Migrar a Dagster, Prefect o Airflow
- **Esfuerzo:** L (semanas)
- **Impacto:** 🔥 alto futuro
- **Razón:** Hoy es `runner.py` custom. Los orquestadores modernos dan UI de runs, retry con backoff, lineage visual, scheduling, alerts on failure, parametrización por run, todo gratis.
- **Recomendación:** evaluar Dagster primero (mejor DX). Migración por jobs incremental, no big-bang.

#### C.1.2 dbt para Silver → Gold
- **Esfuerzo:** L
- **Impacto:** alto
- **Razón:** Los `gold/marts.py` y las agregaciones son el caso de uso ideal de dbt. Lineage automática, tests declarativos, docs auto-generadas. Mantiene Python para Bronce → Silver y dbt para Silver → Gold.

#### C.1.3 Limpiar scripts huérfanos
- **Esfuerzo:** M
- **Impacto:** medio (claridad)
- **Razón:** Inventario detectado en raíz de `ETL/`:
  - `check_bronce.py`, `check_facts.py`, `check_cols.py`, `check_tables.py`, `check_locks.py`, `check_schema.py`, `check_schema_fact.py` — 7 archivos
  - `test_bottleneck.py`, `test_homologador_batch.py`, `test_sp_campana.py`, `test.py` — 4 archivos
  - `trace_queries.py`
  - `scratch/`
  - Más de 30 scripts en `ETL/tools/` (varios `audit_ev*.py`, `auditar_*.py`, etc.)
- **Acción:** mover los útiles a `ETL/tools/` con nombres claros, borrar los efímeros.

#### C.1.4 `dim_geografia_v2.py` vs `dim_geografia.py`
- **Esfuerzo:** S
- **Impacto:** bajo
- **Razón:** Duplicado claro en `ETL/silver/dims/`. Uno de los dos es el activo y el otro está muerto. Identificar cuál corre el pipeline y borrar el otro.

#### C.1.5 Versionamiento de schemas con `pandera` o `great_expectations`
- **Esfuerzo:** L
- **Impacto:** alto calidad
- **Razón:** Hoy las DQ rules viven en `dq/reglas.py` y `dq/validador.py`, probablemente como SQL imperativo. `pandera` permite declarar el contrato del DataFrame en Python tipado; `great_expectations` da suite completa de DQ con docs y reportes.

---

### C.2 Performance / Confiabilidad

#### C.2.1 `polars` en vez de `pandas`
- **Esfuerzo:** M-L
- **Impacto:** alto
- **Razón:** Polars es 5-10x más rápido que Pandas en transformaciones, paraleliza automáticamente y usa menos memoria. Migración por archivo, no big-bang. API similar pero no idéntica.

#### C.2.2 Bulk insert vs row-by-row
- **Esfuerzo:** S
- **Impacto:** alto si hay row-by-row
- **Razón:** Verificar que las inserciones en Silver y Gold usen `executemany` o `BULK INSERT` de SQL Server. Si hay un loop con `INSERT ... VALUES` row-by-row, el cuello de botella es ahí.

#### C.2.3 Particionamiento de fact tables por fecha
- **Esfuerzo:** L
- **Impacto:** alto a futuro
- **Razón:** SQL Server soporta `PARTITION BY` que acelera queries WHERE por rango de fechas y permite archivado/drop de particiones viejas sin lockear la tabla. Recomendado cuando las facts crucen 100M filas.

#### C.2.4 Retry con backoff exponencial en `bronce/cargador.py`
- **Esfuerzo:** S
- **Impacto:** alto
- **Razón:** Si un Excel está temporalmente corrupto, bloqueado por OneDrive sync o el share network falla, la corrida muere. Retry con backoff (1s, 2s, 4s, 8s) recupera transparentemente.

#### C.2.5 Idempotencia explícita
- **Esfuerzo:** M
- **Impacto:** alto
- **Razón:** El patrón actual usa `WHERE NOT EXISTS` para dedupe. Documentar la garantía formalmente + agregar tests que verifiquen que correr 2x el mismo pipeline da el mismo resultado.

---

### C.3 Observability ETL

#### C.3.1 Métricas Prometheus
- **Esfuerzo:** M
- **Impacto:** alto
- **Razón:** Rows procesadas por minuto, latency p95 por step, fallos por step, tamaño de cuarentena. Exportar a Prometheus + Grafana habilita alertas reales.

#### C.3.2 OpenTelemetry tracing end-to-end
- **Esfuerzo:** L
- **Impacto:** alto
- **Razón:** Desde el upload del Excel hasta el row en Gold, todo en un solo trace. Identifica cuello de botella exacto. Cross-stack: portal upload → backend route → ETL job → SQL.

#### C.3.3 Alertas Slack/email cuando circuit breaker dispara
- **Esfuerzo:** S
- **Impacto:** alto
- **Razón:** Hoy el circuit breaker (`utils/circuit_breaker.py`) probablemente solo loguea. Wirearlo a Slack webhook hace que el equipo se entere sin tener que mirar logs.

#### C.3.4 Data quality dashboards
- **Esfuerzo:** M
- **Impacto:** alto
- **Razón:** Leer `dq/cuarentena.py` y `dq/validador.py` para crear dashboard con tendencias: tasa de rechazo histórica, top reglas que fallan, cobertura MDM por catálogo.

---

## D. Cross-cutting (DB / Deploy / DX / Observability)

### D.1 Base de datos

#### D.1.1 Cambiar collation de columnas a `Modern_Spanish_CI_AI`
- **Esfuerzo:** M (requiere DBA + migration)
- **Impacto:** alto
- **Razón:** Fix estructural del bug de accent-sensitivity. Hoy se aplica `COLLATE Modern_Spanish_CI_AI` por query en geografía (commit `d4054d7`). Cambiar la collation default elimina la necesidad.
- **Cuidado:** requiere ALTER de cada columna afectada + verificación de índices (los índices con collation distinta no se usan automáticamente).

#### D.1.2 Index review de queries top-10
- **Esfuerzo:** M
- **Impacto:** alto
- **Razón:** `EXPLAIN ANALYZE` (en SQL Server: `SET STATISTICS IO ON`) sobre las 10 queries más usadas del portal. Probable hallazgo: falta índice en Silver para los JOINs frecuentes de dashboard y catálogos.

#### D.1.3 Read replicas
- **Esfuerzo:** L
- **Impacto:** alto a escala
- **Razón:** Separar carga de lectura (reportes pesados) de carga de escritura (ETL). Solo justificado cuando hay contención real medida.
- **Recomendación:** NO atacar sin medición previa de carga.

#### D.1.4 Backup verification automático
- **Esfuerzo:** M
- **Impacto:** alto reliability
- **Razón:** ¿Hay restore tests automáticos? Sin probar el restore, no hay backup. Job semanal que restaura un backup en una DB efímera y corre queries de smoke.

---

### D.2 Deploy / Infrastructure

#### D.2.1 Dockerizar todo el stack
- **Esfuerzo:** L
- **Impacto:** alto
- **Razón:** Dockerfile para FastAPI + Next + Runner. `docker-compose.yml` para dev. Resuelve "funciona en mi máquina" y onboarding lento de nuevos devs.

#### D.2.2 CI/CD pipeline (GitHub Actions / GitLab CI)
- **Esfuerzo:** M
- **Impacto:** alto
- **Razón:** Auto-deploy a staging en push a main. Patrón mínimo:
  - Lint + typecheck + tests en cada PR
  - Build + deploy automático en merge
  - Promoción manual de staging a producción

#### D.2.3 Reemplazar `acp_start.py` por systemd / Windows Service
- **Esfuerzo:** M
- **Impacto:** alto reliability
- **Razón:** Hoy el lanzador es un script que el operador corre manualmente. En producción debería ser un servicio del SO con restart-on-crash, log rotation, dependencias declaradas.

#### D.2.4 Environment promotion (staging + prod separados)
- **Esfuerzo:** L
- **Impacto:** alto
- **Razón:** Hoy parece solo ambiente dev. Sin staging, los cambios van directo a prod sin smoke. Sin separación de DB schemas versionados (D.1.x + B.2.3), las migrations también van a ciegas.

#### D.2.5 Health monitoring externo
- **Esfuerzo:** S
- **Impacto:** alto
- **Razón:** UptimeRobot, Healthchecks.io, o Pingdom monitoreando el endpoint `/health` desde fuera de la red interna. Detecta caídas que el monitoreo interno (que vive en el mismo server) no ve.

---

### D.3 Observability cross-stack

#### D.3.1 Sentry para errores frontend + backend
- **Esfuerzo:** S
- **Impacto:** 🔥 alto
- **Razón:** El `ErrorBoundary` del portal ya tiene hook `onError` esperando un SDK. Sentry da:
  - Stack traces con sourcemaps
  - Breadcrumbs de acciones del usuario
  - Release tracking
  - Alertas por threshold
- **Recomendación:** este es el item #1 a hacer ya.

#### D.3.2 Logs centralizados (Loki / ELK / Datadog)
- **Esfuerzo:** M
- **Impacto:** alto
- **Razón:** Hoy los logs viven en disco local rotando con `RotatingFileHandler`. Sin agregación cross-host, debuggear un incident es SSH-and-grep. Loki es la opción más barata; Datadog la más completa.

#### D.3.3 APM (Application Performance Monitoring)
- **Esfuerzo:** M
- **Impacto:** alto
- **Razón:** DataDog APM, New Relic, o Tempo + Grafana. Identifica queries SQL lentas en producción con stack trace, no solo logs.

#### D.3.4 Real User Monitoring (RUM)
- **Esfuerzo:** S
- **Impacto:** medio
- **Razón:** Web Vitals reales de usuarios reales, no solo synthetic. Sentry y Datadog incluyen RUM. Permite detectar regresiones de UX por geo / device / red.

---

### D.4 Developer Experience

#### D.4.1 `pnpm` en vez de `npm`
- **Esfuerzo:** S
- **Impacto:** medio DX
- **Razón:** Install 3x más rápido, disk usage menor (hard links). Monorepo-ready si en el futuro hay más apps.

#### D.4.2 `uv` en vez de `pip`
- **Esfuerzo:** S
- **Impacto:** alto DX
- **Razón:** `uv` (de Astral) es 10-100x más rápido que pip. Drop-in para la mayoría de casos. `pip install -r requirements.txt` → `uv pip install -r requirements.txt`.

#### D.4.3 Husky + lint-staged
- **Esfuerzo:** S
- **Impacto:** alto DX
- **Razón:** Pre-commit hooks que corren eslint --fix + tsc + pytest en archivos modificados. Atrapa errores antes del PR, no en CI.

#### D.4.4 Conventional commits + commitlint
- **Esfuerzo:** S
- **Impacto:** medio
- **Razón:** Habilita changelog automático con `standard-version` o `release-please`. Los commits de esta sesión ya siguen el formato (`feat(...)`, `fix(...)`, etc.), falta enforcer.

#### D.4.5 `.gitattributes` para warnings LF/CRLF
- **Esfuerzo:** S
- **Impacto:** bajo (cosmético)
- **Razón:** Termina los warnings "LF will be replaced by CRLF" en cada commit en Windows. Una línea: `* text=auto eol=lf`.

#### D.4.6 devcontainer / GitHub Codespaces
- **Esfuerzo:** M
- **Impacto:** alto futuro
- **Razón:** Onboarding nuevo dev en 5 minutos con un `.devcontainer/devcontainer.json`. Especialmente útil si llegan colaboradores externos.

---

### D.5 Documentación

#### D.5.1 ADRs (Architecture Decision Records)
- **Esfuerzo:** S
- **Impacto:** alto
- **Razón:** `docs/decisiones/` ya tiene 2 docs (medición catálogos y bundle analyzer). Sistemizar el patrón con un template fijo. Cada decisión técnica importante se documenta así.

#### D.5.2 Diagramas C4 del sistema
- **Esfuerzo:** M
- **Impacto:** medio
- **Razón:** Diagramas de contexto, contenedores, componentes. Sirve para onboarding y discusión de arquitectura. Herramienta: structurizr, mermaid C4.

#### D.5.3 Runbooks operacionales
- **Esfuerzo:** M
- **Impacto:** alto reliability
- **Razón:** `RUNBOOK_CONTROL_PLANE_ETL.md` ya existe. Replicar el patrón para incidentes comunes:
  - DB caída
  - ETL stuck en una corrida
  - Portal sin servir
  - Backups perdidos
  - Reset de password admin
  - Recovery de cuarentena masiva

---

## Recomendación — Top 5 ROI para aplicar primero

Si tengo que elegir 5 items para el próximo trimestre, ordenados por impacto/esfuerzo:

| # | Item | Esfuerzo | Impacto | Por qué |
|---|---|---|---|---|
| 1 | **D.3.1 Sentry** | S | 🔥 alto | Visibilidad inmediata de errores en prod. El `ErrorBoundary` ya tiene el hook, solo falta el SDK. |
| 2 | **B.2.5 Logging estructurado JSON + correlation IDs** | M | alto | Sin esto no se puede correlacionar un error frontend con su trace backend. Habilita observability decente. |
| 3 | **D.1.2 Index review de queries top-10** | M | alto | Bajo riesgo, alto impacto de performance medible. Probable hallazgo: índices faltantes en Silver. |
| 4 | **C.1.3 + C.1.4 Cleanup ETL** | M | medio | Más de 30 scripts huérfanos en `ETL/tools/` y duplicado `dim_geografia_v2`. Reduce confusión sin riesgo. |
| 5 | **B.2.2 OpenAPI tipado + `openapi-typescript`** | M | alto | Cierra el drift cliente/server de raíz. Cada endpoint nuevo genera tipos automáticos. |

---

## Lo que NO recomiendo atacar ahora

| Item | Razón |
|---|---|
| **A.1.5 Preact** | Savings reales pero altísimo riesgo por edge cases en libraries con React-internals. |
| **C.1.1 Migrar a Dagster/Airflow** | Refactor de semanas, sin pain real probado en el runner actual. Esperar a que duela. |
| **A.2.4 i18n** | Solo si hay roadmap real de internacionalización. Hoy es premature. |
| **D.1.3 Read replicas** | Premature optimization sin medición de carga. Atacar primero D.1.2. |
| **C.2.3 Particionamiento de fact tables** | Solo si las queries lentas lo apuntan y las facts crucen 100M filas. |
| **A.1.3 Virtualizar lineage-graph** | Sin profiling no se justifica. Medir DevTools primero. |

---

## Anexo — Items menores ya identificados (pendientes residuales)

Lista de pendientes detectados durante la sesión que no entran al catálogo principal por triviales:

- 8 lugares con `.toLowerCase().includes()` no migrados a `normalizeForSearch` (textos en inglés, bajo riesgo)
- 8 archivos `test-results/` dirty desde el inicio de sesión (limpieza Playwright)
- PID 7776 zombi en puerto 8000 (workaround: backend en 8810, reboot resuelve)
- TruncationWarning huérfano si los catálogos de Variedades/Personal no crecen
- `next.config.ts` mantiene `withBundleAnalyzer()` que no funciona en Turbopack (reemplazar por wrapper de `next experimental-analyze`)
- Bug pre-existente `paso.mensajeError` en `etl-run-detail-client.tsx` (fix aplicado en working tree, pendiente commit del user)

---

**Próxima revisión sugerida:** después de ejecutar los Top 5, re-correr este catálogo para ver qué emergió como nueva prioridad.
