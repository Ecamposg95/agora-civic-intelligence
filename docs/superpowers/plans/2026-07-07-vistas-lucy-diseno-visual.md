# Estilización visual de las vistas de Lucy — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Cada agente de UI DEBE invocar `frontend-design`; las tareas de gráficas DEBEN invocar `dataviz`.

**Goal:** Elevar de forma uniforme y ambiciosa las 16 pantallas que ve la Coordinadora (Lucy), combinando storytelling de datos y acabado premium, con un giro de tono cálido + humano — solo markup/estilo/viz, sin cambios de comportamiento.

**Architecture:** Sistema primero, luego aplicar en olas. La Fase 0 afina los tokens globales (`index.css` + `tailwind.config.js`) hacia neutros cálidos + secundario coral, y sube de nivel el kit compartido (`components/ui`, `components/charts`). Las olas A/B/C conforman cada pantalla al kit por arquetipo (dashboards, listas, formularios). Cada ola en worktree aislado, merge incremental a `main`.

**Tech Stack:** React 18 + TypeScript + Vite + Tailwind (tokens CSS `rgb(var(--c-*) / <alpha>)`), Vitest, tema dark/light por clase `.dark`/`.light` en root.

## Global Constraints

- **Cero cambios de comportamiento:** props, handlers, llamadas API, lógica condicional y rutas quedan byte-for-byte. Solo markup, clases/estilo y viz.
- **No se agregan endpoints ni datos backend.** Si un StatCard necesita un delta que la API no da, se muestra sin delta (no se inventa).
- **Acento principal = cian/teal.** El coral (`--c-warm`) es secundario de realce, **nunca** semántico. Semántica reservada: `ok`/`amber`/`critical` con icono+label, nunca color solo.
- **Ambos temas** (`.dark` y `.light`) con el mismo cuidado; foco visible; `prefers-reduced-motion` respetado.
- **Verificación por tarea/ola:** `cd frontend && npm run build` (typecheck + Vite) y `npm run test` (vitest) **verdes** antes de commit.
- **Tokens son "R G B" triplets** para `--c-*` (ej. `--c-bg: 247 245 242;`); los `--chart-*` son **hex** (ej. `--chart-2: #c65b45;`).
- **DRY:** evolucionar los componentes existentes (`MetricCard`, `DataTable`, `Sparkline`), no duplicarlos.

---

## File Structure

**Fase 0 — tokens + kit (una sola fuente de verdad):**
- Modify `frontend/src/index.css` — re-tonar `.dark`/`.light` a cálido, añadir `--c-warm`/`--c-warm-soft`, atenuar `--grid-line`/glows, calentar auras.
- Modify `frontend/src/tailwind.config.js` — añadir color `warm`.
- Modify `frontend/src/components/ui/MetricCard.tsx` — tono `warm` + línea de contexto/meta.
- Create `frontend/src/components/charts/ChartFrame.tsx` — wrapper temático (título, leyenda, estados vacío/carga).
- Create `frontend/src/components/charts/AreaTrend.tsx` — serie de tendencia con endpoint destacado.
- Create `frontend/src/components/charts/Bars.tsx` — barras de magnitud (1 tono).
- Modify `frontend/src/components/charts/Donut.tsx` — alinear a `ChartFrame` + gaps + leyenda con valores.
- Modify `frontend/src/components/ui/DataTable.tsx` — shell v2 (sticky header, hover, densidad).
- Create `frontend/src/components/ui/CellBar.tsx` — mini-viz de cobertura en celda.
- Create `frontend/src/components/ui/StatusPill.tsx` — pill de estado semántica.
- Create `frontend/src/components/ui/Avatar.tsx` — avatar de iniciales (brand|warm).
- Create `frontend/src/components/ui/SectionHeading.tsx` — eyebrow + punto de acento.
- Modify `frontend/src/components/ui/DataState.tsx` — vacío/carga/error unificados (si hace falta).

**Olas A/B/C — pantallas (conformidad al kit):** archivos listados por tarea.

---

## FASE 0 — Tokens + kit compartido

### Task 1: Re-tonar tokens a cálido + color `warm`

**Files:**
- Modify: `frontend/src/index.css` (bloques `.dark` y `.light`, clases `.grid-backdrop`/`.aura`)
- Modify: `frontend/src/tailwind.config.js` (colors)

**Interfaces:**
- Produces: nuevos tokens `--c-warm`, `--c-warm-soft` (triplets) y clase Tailwind `warm` (`bg-warm`, `text-warm`, `border-warm`). `--c-*` neutros re-tonados a cálido. Consumidos por todo el kit y las pantallas.

- [ ] **Step 1: Re-tonar `.dark` (valores cálidos)** — reemplazar en el bloque `.dark` de `index.css`:

```css
--c-bg: 15 12 11;            /* #0f0c0b carbón cálido, no negro puro */
--c-bg-sunken: 10 8 7;
--c-panel: 23 18 17;         /* #171211 */
--c-panel-raised: 30 24 22;  /* #1e1816 */
--c-panel-hover: 37 29 26;   /* #251d1a */
--c-line: 43 35 32;          /* #2b2320 */
--c-line-strong: 62 51 45;   /* #3e332d */
--c-ink: 241 234 229;        /* #f1eae5 */
--c-ink-muted: 178 164 156;  /* #b2a49c */
--c-ink-faint: 124 109 100;  /* #7c6d64 */
--c-warm: 242 138 108;       /* #f28a6c coral (nuevo) */
--c-warm-soft: 246 169 142;  /* #f6a98e */
/* accent/teal/amber/critical/ok SIN cambio */
--chart-2: #f28a6c;          /* era #f5b53d — el 2º categórico ahora es coral */
--chart-5: #a99a8e;          /* neutro cálido */
--chart-grid: #2b2320; --chart-axis: #7c6d64;
--grid-line: rgba(242,138,108,0.035);  /* atenuar + calentar */
--aura-cyan: rgba(45,212,191,0.10); --aura-teal: rgba(242,138,108,0.10);
--glow: 0 0 16px -8px rgba(242,138,108,0.4);  /* atenuar glow */
```

- [ ] **Step 2: Re-tonar `.light` (valores cálidos)** — reemplazar en el bloque `.light`:

```css
--c-bg: 247 245 242;         /* #f7f5f2 warm off-white */
--c-bg-sunken: 241 238 233;
--c-panel: 255 255 255;
--c-panel-raised: 250 248 244;  /* #faf8f4 */
--c-panel-hover: 241 236 229;   /* #f1ece5 */
--c-line: 232 225 216;          /* #e8e1d8 */
--c-line-strong: 215 204 190;   /* #d7ccbe */
--c-ink: 33 26 25;              /* #211a19 */
--c-ink-muted: 95 84 79;        /* #5f544f */
--c-ink-faint: 151 138 128;     /* #978a80 */
--c-warm: 198 91 69;            /* #c65b45 coral (nuevo) */
--c-warm-soft: 224 131 107;     /* #e0836b */
--chart-2: #c65b45; --chart-5: #8a7d72;
--chart-grid: #ece5db; --chart-axis: #a99d90;
--grid-line: rgba(198,91,69,0.05);
--aura-cyan: rgba(13,148,136,0.08); --aura-teal: rgba(198,91,69,0.07);
--glow: 0 0 14px -8px rgba(198,91,69,0.35);
```

- [ ] **Step 3: Añadir `warm` a Tailwind** — en `tailwind.config.js`, dentro de `colors`, junto a `teal`/`amber`:

```js
warm: { DEFAULT: ch("--c-warm"), soft: ch("--c-warm-soft") },
```

- [ ] **Step 4: Suavizar el backdrop** — en `.grid-backdrop` (index.css), aumentar el tamaño de celda del grid (de `44px` a `72px`) para que el patrón sea menos "HUD". Mantener la clase; solo cambia `background-size`.

- [ ] **Step 5: Verify build + visual**

Run: `cd frontend && npm run build`
Expected: PASS. Abrir la app (`npm run dev`) y confirmar que dark y light se ven cálidos, sin grid militar, con coral disponible (`bg-warm`).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/index.css frontend/src/tailwind.config.js
git commit -m "style(tokens): warm neutrals + coral secondary, softened backdrop"
```

---

### Task 2: MetricCard → StatCard v2 (tono warm + contexto/meta)

**Files:**
- Modify: `frontend/src/components/ui/MetricCard.tsx`
- Test: `frontend/src/components/ui/__tests__/MetricCard.test.tsx`

**Interfaces:**
- Consumes: `AnimatedNumber`, `Sparkline` (existentes).
- Produces: `MetricCard` con `tone` extendido a `"accent"|"teal"|"warm"|"warning"|"critical"` y prop nueva `context?: string` (línea de meta/sub bajo el número). Backward-compatible (props previas intactas).

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import { MetricCard } from "../MetricCard";

test("renders warm tone with context line and delta", () => {
  render(<MetricCard label="Promovidos" value="3,502" tone="warm" delta="8.2%" context="meta 4,000" />);
  expect(screen.getByText("Promovidos")).toBeInTheDocument();
  expect(screen.getByText("3,502")).toBeInTheDocument();
  expect(screen.getByText("meta 4,000")).toBeInTheDocument();
  expect(screen.getByText("8.2%")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/ui/__tests__/MetricCard.test.tsx`
Expected: FAIL (no `warm` tone / no `context` render).

- [ ] **Step 3: Implement** — añadir a `MetricCard.tsx`: (a) `warm` en `type Tone` y en el mapa `TONE` con `{ text: "text-warm", glow: "shadow-glow", stroke: "var(--c-warm)"... }` usando `rgb(var(--c-warm))`; (b) prop `context?: string` renderizada como `<div className="mt-1 text-xs text-ink-faint">{context}</div>` bajo el número. Mantener todo lo demás.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/ui/__tests__/MetricCard.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/MetricCard.tsx frontend/src/components/ui/__tests__/MetricCard.test.tsx
git commit -m "feat(ui): MetricCard warm tone + context/meta line"
```

---

### Task 3: ChartFrame (wrapper temático)

**Files:**
- Create: `frontend/src/components/charts/ChartFrame.tsx`
- Test: `frontend/src/components/charts/__tests__/ChartFrame.test.tsx`

**Interfaces:**
- Produces: `<ChartFrame title caption? legend? empty? loading?>{children}</ChartFrame>` — card premium con título/caption, slot de leyenda, y estados vacío/carga (usa `SkeletonCard`/`DataState`). `legend?: {label:string; color:string}[]`.

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import { ChartFrame } from "../ChartFrame";

test("shows empty state when empty", () => {
  render(<ChartFrame title="Casos" empty><svg/></ChartFrame>);
  expect(screen.getByText(/sin datos/i)).toBeInTheDocument();
});
test("renders legend swatches", () => {
  render(<ChartFrame title="Casos" legend={[{label:"Pendiente",color:"var(--chart-1)"}]}><svg/></ChartFrame>);
  expect(screen.getByText("Pendiente")).toBeInTheDocument();
});
```

- [ ] **Step 2: Verify fails** — Run: `cd frontend && npx vitest run src/components/charts/__tests__/ChartFrame.test.tsx` → FAIL.

- [ ] **Step 3: Implement**

```tsx
import type { ReactNode } from "react";

interface LegendItem { label: string; color: string; }
interface ChartFrameProps {
  title: string; caption?: string; legend?: LegendItem[];
  empty?: boolean; loading?: boolean; children: ReactNode;
}
export function ChartFrame({ title, caption, legend, empty, loading, children }: ChartFrameProps) {
  return (
    <div className="card-premium reveal p-5">
      <div className="flex items-baseline justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold tracking-tight text-ink">{title}</h3>
          {caption && <p className="mt-0.5 text-xs text-ink-faint">{caption}</p>}
        </div>
      </div>
      <div className="mt-3">
        {loading ? (
          <div className="h-40 animate-pulse rounded-card bg-panel-hover" />
        ) : empty ? (
          <div className="flex h-40 items-center justify-center text-sm text-ink-faint">Sin datos para mostrar</div>
        ) : children}
      </div>
      {legend && legend.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-3 text-xs text-ink-muted">
          {legend.map((l) => (
            <span key={l.label} className="inline-flex items-center gap-1.5">
              <i className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: l.color }} />{l.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Verify passes** — Run same vitest → PASS.
- [ ] **Step 5: Commit** — `git add frontend/src/components/charts/ChartFrame.tsx frontend/src/components/charts/__tests__/ChartFrame.test.tsx && git commit -m "feat(charts): ChartFrame themed wrapper with empty/loading/legend"`

---

### Task 4: AreaTrend (tendencia con endpoint destacado)

**Files:**
- Create: `frontend/src/components/charts/AreaTrend.tsx`
- Test: `frontend/src/components/charts/__tests__/AreaTrend.test.tsx`

**Interfaces:**
- Produces: `<AreaTrend points={{x:string; y:number}[]} color? />` — SVG responsivo: área con gradiente, línea 2.5px, grid horizontal recesivo (`--chart-grid`), endpoint destacado (círculo r5 + label del último valor), ejes X con labels. `color` default `var(--chart-1)`.

- [ ] **Step 1: Write the failing test**

```tsx
import { render } from "@testing-library/react";
import { AreaTrend } from "../AreaTrend";
test("renders an svg with an accessible label", () => {
  const { container } = render(<AreaTrend points={[{x:"S1",y:10},{x:"S2",y:20}]} />);
  expect(container.querySelector("svg[role='img']")).toBeTruthy();
});
```

- [ ] **Step 2: Verify fails** → FAIL.
- [ ] **Step 3: Implement** — SVG con `viewBox="0 0 560 200"`, escala Y a `max(points.y)`, path de área (gradiente `--chart-1` .26→0), path de línea (`strokeWidth 2.5`, linecap/linejoin round), 3 gridlines horizontales `--chart-grid`, `circle` r5 en el último punto (`stroke=var(--c-panel)`), `<text>` con el último valor (formato `Intl.NumberFormat`), labels X en `--chart-axis`. `role="img"` + `aria-label` con el último valor. Sigue las specs de `dataviz/marks-and-anatomy.md`.
- [ ] **Step 4: Verify passes** → PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(charts): AreaTrend series with emphasized endpoint"`

---

### Task 5: Bars (magnitud, un tono)

**Files:**
- Create: `frontend/src/components/charts/Bars.tsx`
- Test: `frontend/src/components/charts/__tests__/Bars.test.tsx`

**Interfaces:**
- Produces: `<Bars items={{label:string; value:number}[]} color? highlightFirst? />` — barras horizontales con track, fill 1 tono (`--c-accent` por defecto; `highlightFirst` pinta la primera con `--c-warm`), valor a la derecha con `tabular-nums`. Ancho por `value/max`.

- [ ] **Step 1: Write failing test**

```tsx
import { render, screen } from "@testing-library/react";
import { Bars } from "../Bars";
test("renders each bar label and value", () => {
  render(<Bars items={[{label:"4121",value:612},{label:"4118",value:540}]} />);
  expect(screen.getByText("4121")).toBeInTheDocument();
  expect(screen.getByText("612")).toBeInTheDocument();
});
```

- [ ] **Step 2: Verify fails** → FAIL.
- [ ] **Step 3: Implement** — grid `64px 1fr 52px` por fila; track `bg` mezcla de `ink-faint`; fill `background: var(--c-accent)` (o `--c-warm` si `highlightFirst && index===0`), ancho `${(value/max)*100}%`; valor `tabular-nums text-ink font-semibold`.
- [ ] **Step 4: Verify passes** → PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(charts): Bars magnitude primitive"`

---

### Task 6: Donut → alinear a ChartFrame + gaps + leyenda con valores

**Files:**
- Modify: `frontend/src/components/charts/Donut.tsx`
- Test: `frontend/src/components/charts/__tests__/Donut.test.tsx` (crear si no existe)

**Interfaces:**
- Produces: `<Donut segments={{label:string; value:number; color:string}[]} centerLabel? />` — donut SVG con `pathLength=100`, gap de ~1.5 entre segmentos, hueco central con total + `centerLabel`. Devuelve también la `legend` para pasarla a `ChartFrame`.

- [ ] **Step 1: Write failing test** — render con 2 segmentos, aserta que existe el `<svg role="img">` y el total en el centro.
- [ ] **Step 2: Verify fails** → FAIL.
- [ ] **Step 3: Implement** — refactor a la firma `segments`; calcular offsets acumulados (patrón `stroke-dasharray "<pct> <100-pct>"`, `stroke-dashoffset = 25 - startPct`); restar ~1.5 a cada `pct` para el gap; texto central = suma de `value` + `centerLabel`. **No** cambiar consumidores en esta tarea (se ajustan en sus pantallas).
- [ ] **Step 4: Verify passes** → PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(charts): Donut segments API with gaps + center total"`

---

### Task 7: Table shell v2 (DataTable + CellBar + StatusPill + Avatar)

**Files:**
- Modify: `frontend/src/components/ui/DataTable.tsx`
- Create: `frontend/src/components/ui/CellBar.tsx`, `frontend/src/components/ui/StatusPill.tsx`, `frontend/src/components/ui/Avatar.tsx`
- Test: `frontend/src/components/ui/__tests__/tableshell.test.tsx`

**Interfaces:**
- Produces:
  - `DataTable`: header sticky (`position:sticky top-0 bg-panel-raised`), `tbody tr:hover` → `bg-panel-hover`, densidad consistente (padding `12px 18px`), borde `border-line`. Mantener su API de columnas actual.
  - `<CellBar value={0..100} />` — mini-barra de cobertura + `%` (`--c-teal`).
  - `<StatusPill kind="ok"|"warn"|"crit" children />` — pill con punto y color semántico.
  - `<Avatar initials variant="brand"|"warm" />` — cuadro redondeado con iniciales.

- [ ] **Step 1: Write failing test** — render `<CellBar value={92}/>` → aserta "92%"; `<StatusPill kind="ok">Verificado</StatusPill>` → aserta "Verificado"; `<Avatar initials="ML"/>` → aserta "ML".
- [ ] **Step 2: Verify fails** → FAIL.
- [ ] **Step 3: Implement** los tres componentes nuevos + los ajustes de clases en `DataTable` (solo estilos; **sin** tocar su lógica de datos/paginación).
- [ ] **Step 4: Verify passes** → PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(ui): table shell v2 (DataTable polish + CellBar/StatusPill/Avatar)"`

---

### Task 8: SectionHeading + DataState

**Files:**
- Create: `frontend/src/components/ui/SectionHeading.tsx`
- Modify: `frontend/src/components/ui/DataState.tsx` (solo si sus estados no cubren vacío/carga/error de forma unificada)
- Test: `frontend/src/components/ui/__tests__/SectionHeading.test.tsx`

**Interfaces:**
- Produces: `<SectionHeading eyebrow? title note? />` — punto de acento (`--c-warm` gradiente) + título uppercase tracking + nota a la derecha.

- [ ] **Step 1: Write failing test** — render con `title="Casos"` y `note="hoy"`, aserta ambos textos.
- [ ] **Step 2: Verify fails** → FAIL.
- [ ] **Step 3: Implement** SectionHeading. Revisar `DataState`; si ya cubre vacío/carga/error, no modificar (solo confirmar y anotar).
- [ ] **Step 4: Verify passes** → PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(ui): SectionHeading + confirm DataState coverage"`

---

### Task 9: Validar paleta categórica + gate de Fase 0

**Files:** (ninguno nuevo; verificación)

- [ ] **Step 1: Validar la paleta con coral** (light y dark) con el script de dataviz:

Run:
```
node <dataviz-skill>/scripts/validate_palette.js "#0891b2,#c65b45,#0d9488,#be123c,#8a7d72" --mode light
node <dataviz-skill>/scripts/validate_palette.js "#22d3ee,#f28a6c,#2dd4bf,#f4607a,#a99a8e" --mode dark
```
Expected: CVD separation PASS (≥12). Si el coral falla adyacencia, ajustar el paso de coral al más cercano que pase y actualizar `--chart-2` en `index.css` + el mockup.

- [ ] **Step 2: Gate completo de Fase 0**

Run: `cd frontend && npm run build && npm run test`
Expected: build PASS + vitest PASS (baseline 27 + los nuevos de kit).

- [ ] **Step 3: Commit** (si hubo ajuste de paleta) — `git commit -m "style(charts): pin CVD-validated categorical palette with coral"`

---

## OLA A — Overview / dashboards (7 pantallas)

> Cada tarea: worktree/subagente con `frontend-design` + `dataviz`. Patrón común: hero row de `MetricCard` (con `context`/meta y `tone` incl. `warm` en el KPI destacado) → gráficas vía `ChartFrame` + `AreaTrend`/`Donut`/`Bars` → `SectionHeading` entre bloques → backdrop cálido. **Preservar** props/handlers/API/estados. Verificar `npm run build` + `npm run test` verdes; revisar contra el mockup aprobado. Commit al final.

### Task 10: Command Center — `pages/DashboardPage.tsx`
- [ ] Conformar KPIs a `MetricCard` v2 (uno `tone="warm"`), gráficas a `ChartFrame`+primitivas, `SectionHeading`. Preservar countdown, mapa y datos. Build+test+visual. Commit `style(dashboard): kit v2 + warm/human pass`.

### Task 11: Map Explorer — `pages/MapExplorerPage.tsx`
- [ ] Envolver panel lateral/leyenda en el lenguaje del kit (cards premium, SectionHeading), tokens cálidos; no tocar la lógica del mapa MapLibre. Build+test+visual. Commit.

### Task 12: Territorios & Secciones — `modules/territorios/TerritoriosPage.tsx`
- [ ] Franja de KPIs (MetricCard v2) + gráficas a ChartFrame + tabla a Table shell v2 (mini-viz de cobertura por sección). Preservar filtros/mapa. Build+test+visual. Commit.

### Task 13: Panorama afiliación — `modules/militantes/PanoramaMilitantesPage.tsx`
- [ ] KPIs v2 + gráfica(s) a ChartFrame/Donut/Bars + tabla resumen a shell v2. Preservar scoping. Build+test+visual. Commit.

### Task 14: Panorama ciudadano — `modules/atencion/PanoramaAtencionPage.tsx`
- [ ] Re-tune al kit (recién pulido): KPIs a MetricCard v2, gráficas a ChartFrame/Donut, coral en el destacado. Build+test+visual. Commit.

### Task 15: Reportes Ejecutivos — `modules/reportes/ReportesPage.tsx`
- [ ] Gráficas a ChartFrame+primitivas, KPIs v2, SectionHeading. Preservar export/params. Build+test+visual. Commit.

### Task 16: Consola Activistas — `modules/admin/AdminDashboardPage.tsx`
- [ ] KPIs v2 + gráficas a ChartFrame. Preservar scoping admin. Build+test+visual. Commit.

**Gate Ola A:** merge incremental a `main`; `npm run build && npm run test` verdes.

---

## OLA B — Listas / padrones (5 pantallas)

> Patrón común: franja de KPIs de resumen arriba (MetricCard v2) + `DataTable` shell v2 con `Avatar`/`StatusPill`/`CellBar` + `SectionHeading` + estados `DataState`. **Preservar** columnas, filtros, paginación, acciones. Verificar build+test+visual. Commit.

### Task 17: Promovidos — `modules/promovidos/PromovidosPage.tsx`
- [ ] **Mayor salto:** de tabla pelada (~77 líneas) a padrón — franja de KPIs (total, por sección, cobertura), Table shell v2 con CellBar de contexto electoral. Preservar el import/tabla existente. Build+test+visual. Commit.

### Task 18: Padrón de militantes — `modules/militantes/MilitantesListPage.tsx`
- [ ] Table shell v2 (Avatar iniciales, StatusPill de verificación, CellBar de cobertura de datos) + franja de KPIs. Preservar filtros. Build+test+visual. Commit.

### Task 19: Registros (Admin) — `modules/admin/AdminRegistrosPage.tsx`
- [ ] Table shell v2 + KPIs de resumen. Preservar reveal auditado y scoping. Build+test+visual. Commit.

### Task 20: Casos — `modules/atencion/CasosPage.tsx`
- [ ] Re-tune al kit (recién pulido): StatusPill de estado con semáforo SLA, CellBar si aplica, franja de KPIs. Build+test+visual. Commit.

### Task 21: Estructura — `modules/admin/AdminEstructuraPage.tsx`
- [ ] Jerarquía visual con Avatar + SectionHeading + cards del kit. Preservar el árbol/estructura. Build+test+visual. Commit.

**Gate Ola B:** merge incremental; build+test verdes.

---

## OLA C — Formularios / captura (3) + AI Analyst (1)

> Patrón: layout de captura premium por secciones (SectionHeading), estados de éxito con métrica, cards del kit; **sin** tocar validación/lógica de captura. Verificar build+test+visual. Commit.

### Task 22: Afiliar militante — `modules/militantes/CapturaMilitantePage.tsx`
- [ ] Agrupación por secciones con jerarquía, cards premium, estado de éxito con métrica. Preservar toda la lógica del form (883 líneas). Build+test+visual. Commit.

### Task 23: Atender ciudadano — `modules/atencion/CapturaAtencionPage.tsx`
- [ ] Re-tune al kit (recién pulido): SectionHeading, cards, coral en acentos. Preservar OCR/DynamicForm. Build+test+visual. Commit.

### Task 24: Formularios/builder — `modules/atencion/FormBuilderPage.tsx`
- [ ] Re-tune al kit (recién pulido): paleta/tokens cálidos, SectionHeading. Preservar builder + FieldEditor. Build+test+visual. Commit.

### Task 25: AI Analyst / Copiloto — `modules/ai-analyst/AiAnalystPage.tsx`
- [ ] Tratamiento "copiloto" premium (aunque sea preview): card del kit, cálido. Build+test+visual. Commit.

**Gate Ola C:** merge incremental; build+test verdes.

---

## Cierre

### Task 26: Consistency critic + review adversarial + verificación en prod

- [ ] **Step 1: Consistency critic** — subagente que compara las 16 pantallas contra las Reglas de Uniformidad del spec (§6) y entre sí; lista desviaciones (espaciado, uso de coral, KPI vs chart vs tabla, semántica). Corregir inline.
- [ ] **Step 2: Review adversarial del frontend** — subagente read-only que busca defectos (correctness, contratos API intactos, PII, estados) en los cambios. Corregir hallazgos reales.
- [ ] **Step 3: Gate final** — `cd frontend && npm run build && npm run test` verdes; `cd backend && python3 -m pytest -q` verde (no debe haberse tocado, confirmar).
- [ ] **Step 4: Merge final a `main` + push.** El push dispara redeploy Railway — verificar build + healthcheck + una vista de Lucy autenticada (patrón de [[railway-deploy-ops]]).
- [ ] **Step 5: Commit/PR final** — `git commit -m "style(lucy): warm+human visual system across all 16 coordinator views"`

---

## Self-Review

- **Cobertura del spec:** §4 tokens → Task 1; StatCard v2 → Task 2; kit de gráficas → Tasks 3-6; table shell → Task 7; scaffolding → Task 8; validación paleta → Task 9; overview/listas/forms/preview (§5) → Olas A/B/C (Tasks 10-25); reglas de uniformidad + verificación (§6-7) → Task 26. Sin huecos.
- **Placeholders:** las tareas de pantalla son de **conformidad** (aplicar kit + preservar comportamiento + verificar); el ejecutor lee cada archivo y aplica el kit definido en Fase 0. No hay "TBD". El código completo vive en las tareas de kit (Fase 0), que es lo reutilizable.
- **Consistencia de tipos:** `MetricCard` (tone incl. `warm`, `context`), `ChartFrame` (title/legend/empty/loading), `AreaTrend` (points), `Bars` (items/highlightFirst), `Donut` (segments/centerLabel), `CellBar` (value), `StatusPill` (kind), `Avatar` (initials/variant), `SectionHeading` (eyebrow/title/note) — nombres usados consistentemente en Olas A/B/C.
