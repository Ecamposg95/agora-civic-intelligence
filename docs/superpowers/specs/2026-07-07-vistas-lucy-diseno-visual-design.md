# Diseño — Estilización visual de las vistas de Lucy (cálida + humana)

**Fecha:** 2026-07-07
**Autor:** Emmanuel Campos (con Claude)
**Estado:** Aprobado en brainstorming — pendiente de revisión de spec

---

## 1. Contexto y objetivo

Ágora es una plataforma GovTech API-first. El frontend consume `/api/*` y ya tiene un
sistema de diseño maduro ("command-center"): tokens CSS dark+light, acentos cian/teal/ámbar,
tokens de gráficas (`--chart-1..5`), glows/auras, y un kit compartido (`MetricCard`,
`Sparkline`, `AnimatedNumber`, `DataTable`, `charts/Donut`, `charts/StackedBars`).

El problema **no** es falta de marca: es que la marca está aplicada **de forma desigual** entre
pantallas (algunos panoramas ricos, otros —como Promovidos, ~77 líneas— casi pelados), el
**storytelling de datos** se queda corto (KPIs sin contexto de tendencia/meta), y la estética
actual lee como un **war-room táctico** (negro puro, glow neón, grid tipo HUD) que resulta
fría para su usuaria principal.

**Objetivo:** elevar de forma **uniforme y ambiciosa** las 16 pantallas que ve la
Coordinadora (rol `coordinador`, "Lucy"), combinando **storytelling de datos** y **acabado
premium**, con un giro de tono **cálido + humano** apropiado para el perfil de usuaria.

## 2. Usuaria

- Perfil dominante: **mujeres ejecutivas, muy visuales.** Deciden de un vistazo; valoran
  claridad, calidez y confianza por encima de densidad técnica o estética "sci-fi".
- Implicación de diseño (sin estereotipos): mantener el rigor y la sofisticación, pero bajar
  la frialdad táctica — neutros tibios, más aire, elementos humanos (nombres, avatares),
  geometría amable, glow atenuado. Confiable y cercano, no war-room.

## 3. Alcance

### 3.1 Pantallas objetivo (16 vistas de Lucy)

Calculadas con el gating real de `frontend/src/modules/registry.ts` (rol `coordinador`):

**Overview / dashboards (7):** Command Center (`/`), Map Explorer (`/maps`), Territorios &
Secciones (`/territorios`), Panorama afiliación (`/militantes`), Panorama ciudadano
(`/atencion`), Reportes Ejecutivos (`/reportes`), Consola Activistas (`/admin`).

**Listas / padrones (5):** Promovidos (`/promovidos`), Padrón de militantes
(`/militantes/lista`), Registros Admin (`/admin/registros`), Casos (`/atencion/casos`),
Estructura (`/admin/estructura`).

**Formularios / captura (3):** Afiliar militante (`/militantes/captura`), Atender ciudadano
(`/atencion/captura`), Formularios/builder (`/atencion/formularios`).

**Preview (1):** AI Analyst / Copiloto (`/ai-analyst`).

> Los 4 módulos de **Atención** se pulieron hace poco (2026-07-06). Reciben solo el
> **re-tune de tokens** + conformidad al kit, no un rediseño desde cero.

### 3.2 Decisión de scope: re-tune de tokens **global**

El giro cálido se implementa **re-afinando los tokens neutros/superficie en `index.css`** y
añadiendo un secundario coral. Como los tokens son globales, esto **calienta toda la app**, no
solo las pantallas de Lucy. Se elige a propósito: una app con mitad "cálida" y mitad "fría"
se vería rota. El cambio es de neutros/superficies + un color nuevo (no funcional, bajo
riesgo). **Punto a confirmar en la revisión del spec.**

### 3.3 No-goals

- No cambiar comportamiento: props, handlers, llamadas API, lógica condicional y rutas quedan
  **byte-for-byte**. Solo markup, clases/estilo y viz.
- No refactor no relacionado. No tocar backend salvo que un dato de storytelling ya exista en
  la API (no se agregan endpoints en este trabajo).
- No cambiar el color de acento principal (sigue cian/teal); el coral es **secundario**.
- No romper accesibilidad ni los colores semánticos (bien/alerta/crítico).

## 4. Dirección estética (validada en mockup)

Mockup aprobado: `direccion-visual` v2 (cálida + humana), construido con tokens reales.

- **Neutros tibios** (greige) en vez de gris frío; **dark = carbón cálido** (`#0f0c0b`), no
  negro puro.
- **Glow atenuado, sin grid militar.** Atmósfera de auras suaves (cálida + teal).
- **Más aire** (radio 20px, padding generoso, escala de espaciado consistente).
- **Elementos humanos:** avatares con iniciales, presencia ("quién está en línea").
- **Secundario coral** junto al cian/teal: KPI destacado, sparkline de featured, barra líder,
  avatares, punto de sección. **Nunca** para semántica (bien/alerta/crítico se conservan).
- **Tipografía:** sans refinada con jerarquía fuerte (peso/tracking/tamaño) + `tabular-nums`
  en datos. Se evita el cliché "cream + serif"; la calidez viene de color/espaciado/roundness/
  elementos humanos, no de una serif decorativa.

### 4.1 Tokens (extienden/afinan `index.css`)

Valores de referencia del mockup (dark + light). El secundario coral es nuevo; los neutros se
re-tonan a cálido.

```
LIGHT  --bg#f7f5f2 --panel#ffffff --panel-raised#faf8f4 --panel-hover#f1ece5
       --line#e8e1d8 --line-strong#d7ccbe --ink#211a19 --ink-muted#5f544f --ink-faint#978a80
       --accent#0891b2 --teal#0d9488 --warm#c65b45 --warm-soft#e0836b
       --amber#b45309 --critical#be123c --ok#0d9488
       --chart: 1#0891b2 2#c65b45 3#0d9488 4#be123c 5#8a7d72  grid#ece5db axis#a99d90
DARK   --bg#0f0c0b --panel#171211 --panel-raised#1e1816 --panel-hover#251d1a
       --line#2b2320 --line-strong#3e332d --ink#f1eae5 --ink-muted#b2a49c --ink-faint#7c6d64
       --accent#22d3ee --teal#2dd4bf --warm#f28a6c --warm-soft#f6a98e
       --amber#f5b53d --critical#f4607a --ok#2dd4bf
       --chart: 1#22d3ee 2#f28a6c 3#2dd4bf 4#f4607a 5#a99a8e  grid#2b2320 axis#7c6d64
       glows atenuados; --warm-grad y --brand-grad para acentos
```

> Nota: se sustituye `--chart-2` (antes ámbar `#f5b53d`) por coral en la paleta categórica para
> integrar el secundario cálido. La paleta resultante debe **re-validarse** con
> `dataviz/scripts/validate_palette.js` (CVD ≥ 12) antes de fijarla. El ámbar sigue disponible
> como color semántico de alerta.

## 5. Arquitectura de la solución

### Fase 0 — Kit compartido (fundamento, una sola fuente de verdad)

Se consolida/sube de nivel el kit en `frontend/src/components/`, para que las 16 pantallas
consuman los mismos primitivos y la uniformidad sea **por construcción**:

- **StatCard v2** (`ui/MetricCard` evolucionado o nuevo `ui/StatCard`): número grande
  (`AnimatedNumber`) + label + **chip de tendencia/meta** (▲▼ con color semántico o coral de
  featured) + sparkline opcional + variante de acento (`brand` | `warm`). Interfaz clara:
  `{ label, value, delta?, deltaKind?, target?, spark?, accent? }`.
- **Kit de gráficas** (`components/charts/`): un wrapper temático (`ChartFrame`) + primitivas
  (`AreaTrend`, `Donut`, `Bars`) que usan los `--chart-*`, ejes/grid recesivos, leyenda +
  etiquetas directas selectivas, tooltip on-hover, y estados vacío/carga. Regla dataviz: forma
  por trabajo (magnitud→barras 1 tono; composición→donut; tendencia→área con endpoint
  destacado; identidad→categórica en orden fijo, nunca cíclico).
- **Table shell v2** (`ui/DataTable` evolucionado): encabezado premium sticky, hover/zebra,
  densidad, **mini-viz en celda** (barra de cobertura), pills de estado semánticas, avatares,
  y estados vacío/carga (`SkeletonCard`).
- **Scaffolding de página** (`layout/PageHeader`, nuevo `ui/SectionHeading`): eyebrow + título
  display + acciones; punto de acento; entrada `reveal` escalonada; respeta
  `prefers-reduced-motion`.
- **State kit** (`ui/DataState`): vacío/carga/error unificados.

### Fases 1–N — Aplicar por arquetipo (olas)

Cada ola toma un arquetipo y conforma las pantallas al kit:

- **Overview/dashboards (7):** hero row de StatCards con contexto (meta/tendencia) → gráficas
  del kit → jerarquía que cuenta la historia de un vistazo; backdrop cálido.
- **Listas/padrones (5):** table shell v2 + franja de KPIs de resumen arriba + mini-viz en
  celda + filtros premium. **Promovidos** sube de tabla pelada a nivel padrón.
- **Formularios/captura (3):** captura premium por secciones + estados de éxito con métrica
  (patrón ya usado en Atención), sin tocar la lógica.
- **Preview (AI Analyst):** tratamiento "copiloto" premium.

## 6. Reglas de uniformidad (mini design-spec que cada ola sigue)

1. **Grid y espaciado:** escala fija (gaps 16/24/44px; radio 20px; padding de card 20–22px).
2. **Cuándo qué:** resumen (KPIs) antes que detalle; magnitud→barras 1 tono; composición→
   donut; tendencia→área; identidad→categórica en orden fijo.
3. **Color:** acento = cian/teal; coral = secundario de realce (featured/humano), **no**
   semántico; semántica reservada (ok/warn/crit) con icono+label, nunca color solo.
4. **Texto** con tokens de tinta, nunca con el color de serie. `tabular-nums` en columnas de
   datos.
5. **Ambos temas** con el mismo cuidado; foco visible; `prefers-reduced-motion` respetado.
6. Todo primitivo sale del kit central — nada de estilos ad-hoc que dupliquen el kit.

## 7. Ejecución y verificación

- **Sistema primero, luego olas** (evita divergencia; lección de la pasada de Atención).
- **Worktrees aislados** por ola (subagentes en paralelo con `frontend-design` + `dataviz`),
  merge incremental a `main`.
- **Por ola:** `cd frontend && npm run build` (typecheck + Vite) y `npm run test` (vitest)
  **verdes**; revisión visual (mockup como norte).
- **Pasada final de *consistency critic*:** comparar las 16 pantallas contra las reglas §6 y
  entre sí; corregir desviaciones.
- **Review adversarial del frontend** al cierre (no se corrió en pasadas previas salvo
  Atención).
- **Regla dura:** sin cambios de comportamiento; si un StatCard necesita un dato de tendencia
  que la API no da, se muestra sin delta (no se inventa ni se agrega endpoint en este trabajo).

## 8. Riesgos y mitigaciones

- **Divergencia visual entre pantallas** → kit central + reglas §6 + consistency critic.
- **Re-tune global afecta pantallas fuera de Lucy** → es deliberado (evita split-brain);
  cambio de neutros + color, bajo riesgo; confirmar en revisión de spec.
- **Regresión funcional por "solo estilo"** → prohibido tocar props/handlers/API; build+vitest
  por ola; review adversarial final.
- **Paleta categórica con coral no CVD-safe** → re-validar con el script antes de fijar; si
  falla, ajustar el paso de coral al más cercano que pase.
- **Contraste de neutros cálidos** (texto muted sobre panel) → verificar WCAG en ambos temas.

## 9. Orden de trabajo sugerido

1. Fase 0 — tokens (`index.css`) + kit (StatCard v2, ChartFrame+primitivas, Table shell v2,
   SectionHeading, DataState). Validar paleta. Build+test.
2. Ola A — overview/dashboards (7).
3. Ola B — listas/padrones (5).
4. Ola C — formularios/captura (3) + AI Analyst (1).
5. Consistency critic + review adversarial + merge final + verificación en prod.
