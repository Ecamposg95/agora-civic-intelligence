# Sidebar Restyle — Diseño

**Fecha:** 2026-07-09
**Estado:** Aprobado — sidebar más grande, más conciso y congruente.

## Objetivo

El sidebar (`frontend/src/components/layout/Sidebar.tsx` + secciones en
`frontend/src/modules/registry.ts`) se siente apretado, con labels largos y una
sección "Ciudadanía" cajón-de-sastre de 23 ítems. Hacerlo **más grande**
(legible/tocable), **más conciso** (labels cortos, sin contador) y **congruente**
(reagrupado de 5 → 4 grupos coherentes). Solo frontend; sin cambios de rutas ni
backend.

## 1. Tamaño / legibilidad (`Sidebar.tsx`)

- Ancho del panel `w-64` (256px) → `w-[280px]`.
- `navItem`: `text-[13px]` → `text-[14px]`; `py-2` → `py-2.5`; `gap-2.5` → `gap-3`.
- Iconos de ítem: subir a ~20px (donde el ítem controla el tamaño del icono).
- Header: caja del logo `h-9 w-9` → `h-11 w-11`, `LogoMark` 20 → 24; nombre
  "Atenea" `text-sm` → `text-base`.
- Etiquetas de sección: mantener el estilo (uppercase, tracking), pero **quitar
  el contador** (`<span>{items.length}</span>`).

## 2. Concisión — labels cortos (`registry.ts`, campo `label` de cada `ModuleDef`)

Regla: 1–2 palabras, sin paréntesis ni sufijos "& …", reconocible. Solo cambia
el `label` del menú (el `<title>`/encabezado de cada página se queda largo).
Ejemplos (aplicar el mismo criterio al resto de labels largos):

| Antes | Después |
|---|---|
| Command Center | **Inicio** |
| Fuentes de datos | Fuentes |
| Búsqueda global | Búsqueda |
| Activity Analytics | Analítica |
| Map Explorer | Mapa |
| Unidades Económicas | Denue |
| Padrón de militantes | Militantes |
| Atender ciudadano | Atender |
| Captura de Activistas | Activistas |
| Importar promovidos | Importar |
| Panorama afiliación | Afiliación |
| Panorama ciudadano | Panorama |
| Auditoría & Cumplimiento | Auditoría |
| Reportes Ejecutivos | Reportes |
| Historial de ingestas | Ingestas |
| Índice Cívico-Territorial | Índice Cívico |
| Consola Activistas | Consola |
| Registros (Admin) | Registros |
| Alertas & Riesgo Electoral | Alertas |
| Demografía & Censo | Censo |
| Participación Ciudadana | Participación |
| Sentimiento Ciudadano | Sentimiento |
| AI Analyst / Copiloto | Copiloto |
| Estado de México (IEEM) | IEEM |
| Indicadores Nacionales | Indicadores |
| Macro-financiero (Banxico) | Banxico |
| Padrón / Lista Nominal | Padrón |
| Territorios & Secciones | Territorios |
| Economía Territorial | Economía |
| Resultados Electorales | Resultados |

Labels ya cortos (Promovidos, Casos, Minutas, Acuerdos, Tablero, Backlog,
Sprints, Formularios, Usuarios, Estructura, Organización, Campañas,
Configuración, War Room, Plan Territorial, Candidaturas) se dejan igual.

## 3. Congruencia — reagrupar 5 → 4

`ModuleSection` pasa a `"operacion" | "inteligencia" | "administracion"` (se
eliminan `plataforma` y `gobernanza`). Command Center se saca como **ítem suelto
arriba, sin encabezado** ("Inicio").

| Grupo (orden) | Origen | Contenido |
|---|---|---|
| *(sin header)* Inicio | dashboard | Command Center → "Inicio", renderizado arriba sin título de sección |
| **Operación** | `ciudadania` (relabel) | captura, promovidos, militantes, atención, plan territorial, war room, minutas, acuerdos, tablero, backlog, sprints, y los paneles ciudadanos que ya estaban ahí |
| **Inteligencia** | `inteligencia` + ex-`plataforma` (Mapa, Analítica, Fuentes, Búsqueda) | datasets electorales/económicos + herramientas de datos |
| **Administración** | `administracion` + `gobernanza` | usuarios, organización, config + auditoría, registros admin, reportes, ingestas, índice, consola |

`SECTION_LABELS = { operacion: "Operación", inteligencia: "Inteligencia
Electoral", administracion: "Administración" }`; `SECTION_ORDER = ["operacion",
"inteligencia", "administracion"]`.

Cambios de `section` por ítem: `ciudadania`→`operacion` (todos); `plataforma`
(Map/Analytics/Fuentes/Búsqueda)→`inteligencia`; `gobernanza`(todos)→
`administracion`; el dashboard se saca del flujo de secciones (render especial).

## 4. Alcance & verificación

- Archivos: `frontend/src/components/layout/Sidebar.tsx`,
  `frontend/src/modules/registry.ts`. Sin backend, sin rutas nuevas.
- Gate: `npm run build` limpio (type-check) + `npm run test` verde. Verificar que
  cada rol sigue viendo sus ítems (el filtrado por `roles` no cambia) y que el
  ítem activo se resalta bien con el nuevo tamaño.
