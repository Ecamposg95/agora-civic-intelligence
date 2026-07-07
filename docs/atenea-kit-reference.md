# Atenea visual kit — referencia compartida para las olas (A/B/C)

Estás aplicando el kit visual "Atenea" (cálido + humano) a UNA pantalla. El kit ya existe en la rama `feat/atenea-visual-system`. **NO reinventes**: consume estos componentes y tokens.

## Dirección (mockup aprobado)
Cálida + humana + premium. Base de marca cian/teal + **secundario coral** (`--c-warm`) para realce (KPI destacado, avatares, acentos), NUNCA para semántica. Neutros tibios, más aire, elementos humanos (avatares/iniciales), menos glow/grid. Storytelling de datos: resumen antes que detalle, KPIs con contexto (meta/tendencia), gráficas que cuentan la historia de un vistazo. Funciona en dark y light.

## Kit disponible (rutas + API)
- `@/components/ui/MetricCard` — KPI. Props: `label, value|countTo, delta?, deltaDir?("up"|"down"|"flat"), context?(meta/sub), tone?("accent"|"teal"|"warm"|"warning"|"critical"), trend?(number[]), icon?, format?, delay?`. Usa `tone="warm"` en el KPI destacado.
- `@/components/charts/ChartFrame` — wrapper. Props: `title, caption?, legend?({label,color}[]), empty?, loading?`. Envuelve toda gráfica.
- `@/components/charts/AreaTrend` — tendencia. Props: `points({x:string,y:number}[]), color?`. Endpoint destacado.
- `@/components/charts/Bars` — magnitud 1 tono. Props: `items({label,value}[]), color?, highlightFirst?`.
- `@/components/charts/Donut` — composición. API SIN CAMBIO: `data(DonutDatum{name,value,color?}[]), height?, centerLabel?`.
- `@/components/ui/SectionHeading` — `eyebrow?, title, note?`. Entre bloques.
- `@/components/ui/DataTable` — tabla (shell v2 ya pulido). Úsalo tal cual.
- `@/components/ui/CellBar` — `value(0..100)` mini-barra de cobertura en celda.
- `@/components/ui/StatusPill` — `kind("ok"|"warn"|"crit")`, children. Estado semántico con dot+label.
- `@/components/ui/Avatar` — `initials, variant("brand"|"warm")`. Elemento humano.
- `@/components/ui/DataState` — vacío/carga/error. `@/components/ui/AnimatedNumber`, `Sparkline`, `Card`.
- Clases: `card-premium`, `panel`, `reveal` (entrada escalonada, animationDelay), `eyebrow`, `metric-chip`, `grid-backdrop`, `aura`, `text-warm`, `bg-warm`, `text-ink/ink-muted/ink-faint`.

## Reglas duras (NO negociables)
1. **Cero cambios de comportamiento**: no toques props, handlers, llamadas API, lógica condicional, rutas, ni el shape de datos. Solo markup/estilo/viz.
2. Si un dato de contexto (delta/meta) NO existe en lo que la página ya recibe, muéstralo SIN ese dato — no inventes ni agregues fetch/endpoint.
3. Colores desde `--c-*` (triplets) SIEMPRE `rgb(var(--c-*))`; `--chart-*` son hex directo. Coral secundario, nunca semántico.
4. Reutiliza el kit; no dupliques estilos ad-hoc que el kit ya cubre.
5. Ambos temas correctos; foco visible; respeta `prefers-reduced-motion` (usa `reveal`).
6. Preserva accesibilidad y los estados vacío/carga/error existentes (vía DataState).

## Verificación (obligatoria antes de commitear)
- `cd frontend && npm run build` PASA (typecheck + Vite).
- `cd frontend && npm run test` PASA (los tests existentes deben seguir verdes; no cambiaste lógica).
- Revisión visual mental contra la dirección del mockup.

## Entrega
Trabaja en tu worktree. Commit: `style(<area>): apply Atenea kit to <pantalla>` (cuerpo con el trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`). Reporta: rama+SHA, qué cambiaste por archivo (solo estilo/viz), y confirmación de build+test verdes.
