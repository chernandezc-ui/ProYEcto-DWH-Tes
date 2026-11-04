# Bundle analyzer — Portal MDM

**Fecha:** 2026-06-17
**Comando:** `npx next experimental-analyze -o`
**Output:** `Portal_MDM_NEXTJS/Portal-Nextjs/portal-mdm/.next/diagnostics/analyze/`

## Contexto

`@next/bundle-analyzer` (la dependencia configurada en `next.config.ts`)
**no es compatible con Turbopack**, que es el default en Next 16. El comando
oficial es `next experimental-analyze`, que sí funciona con Turbopack.

Resultado al correr `ANALYZE=true npm run build`:

> The Next Bundle Analyzer is not compatible with Turbopack builds, no report will be generated.

## Findings

### Verificación de la lazy-load de Plotly (commit task #3)

Se confirmaron **dos chunks de ~4.5 MB cada uno conteniendo Plotly**:

| Chunk | Tamaño | Contenido |
|---|---|---|
| `0.6dvlzaf-o6i.js` | 4.4 MB | Plotly (instance A) |
| `0c7qp81fgplyr.js` | 4.4 MB | Plotly (instance B) |

**Buena noticia:** ambos son chunks separados (no parte del bundle inicial).
La lazy-load via `next/dynamic` con `ssr: false` está funcionando
correctamente — Plotly solo se descarga cuando se monta `<PlotlyChart>`.

**Pregunta abierta:** ¿por qué dos chunks de Plotly? Posibles causas:
1. Dos consumidores que importan Plotly en contextos distintos (analyst vs executive)
2. Turbopack está creando duplicados por code-splitting agresivo
3. Plotly es importado tanto en `plotly-wrapper.tsx` como en otro lugar

Investigar más adelante si los chunks crecen o si la primera carga del
analyst se siente lenta.

### Resto del bundle (top 10 chunks)

| Tamaño | Tipo |
|---|---|
| 289K x 3 | Chunks de aplicación / Recharts |
| 264K | Probablemente lucide-react |
| 223K | Chunk de aplicación |
| 134K, 110K, 104K | Aplicación |
| 99K | CSS principal (Tailwind compiled) |

Todo dentro de lo esperado para un portal con React 19 + TanStack Query
+ Radix UI + Recharts. Ningún red flag aparte de la duplicación de
Plotly que vale la pena auditar.

## Acción recomendada

1. **No urgente:** investigar por qué Plotly genera dos chunks.
   - Buscar `import.*plotly` en el código
   - Si hay dos consumidores, considerar unificarlos en un solo `plotly-wrapper.tsx`
2. **Pendiente:** considerar reemplazar `@next/bundle-analyzer` por
   un script wrapper que llame `next experimental-analyze -o` y abra el HTML.
   Hoy queda `next.config.ts` con `withBundleAnalyzer()` que no hace nada
   en builds Turbopack.

## Conclusión

P3.3 del audit /impeccable **completado** — el bundle no tiene
red flags. Plotly (la dependencia más pesada) está correctamente
aislada en chunks lazy. La única acción de seguimiento es entender
por qué Plotly aparece dos veces (no bloqueante).
