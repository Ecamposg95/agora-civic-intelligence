# Electoral Intelligence Platform — Master Program Spec

**Date:** 2026-06-18
**Status:** Approved (program shape) — pending spec review
**Type:** Program architecture + roadmap (NOT a single implementation spec). Each sub-project below gets its own spec → plan → implementation cycle.
**Owner:** Ágora Civic Intelligence (Atlas Tech)

## 0. Purpose & locked decisions

Turn Ágora (today: an intelligence layer over reference data) into a full multi-tenant **Electoral Intelligence Platform** spanning intelligence, field operations, war room, and predictive AI — the 31-module blueprint the user provided.

**Locked decisions (from brainstorming, 2026-06-18):**
1. **Deliverable now:** this master program spec only (no code yet).
2. **Tenancy:** **multi-tenant SaaS from day one** — every domain table is scoped by `(tenant_id, campaign_id)`; licensing/separation are first-class.
3. **Value bet:** **intelligence AND operational tracks in parallel.**
4. **Field reality:** a real territorial organization + operational data exist → operational/mobile/war-room modules are near-term real, not theoretical.

**Program approach (A — spine-first, then parallel streams):** build the platform core (SP0) that fixes the canonical model and cross-cutting services; then run the Intelligence stream (SP1) in parallel with the Operational+Mobile stream (SP2→SP3); converge at Engagement (SP4) and War Room (SP5); Predictive/AI (SP6) last. The spine is the shared contract that lets parallel streams not collide.

## 1. Current platform baseline (what we reuse)

Verified against the codebase (2026-06-18):
- **Backend models:** `Organization` (tenant), `User` (UUID/Audit, `UserRole` enum, tenant-bound; superadmin global), `ElectoralArea` (`UUIDMixin+TenantMixin+AuditMixin`, `AreaLevel` enum, geometry), `AuditLog`. Mixins: `UUIDMixin`, `TenantMixin`, `AuditMixin` (soft-delete).
- **Backend routers:** auth (JWT+RBAC+tenant context, forced-password-change gate), users (full CRUD), organizations (CRUD), audit, analytics, intel (WorldBank/IEEM proxies), maps (areas GeoJSON + server-side simplification), sources, health.
- **Frontend:** ~28 modules over a mature design system — `DataTable`, `SegmentedControl`, `DataState`, `SkeletonCard`, charts (Recharts wrappers), `MapCanvas` (MapLibre), `PageHeader`, **dark+light theming** (CSS-variable tokens), module registry driving sidebar/routes with `active|preview|soon` states.
- **Specced, not built:** file-ingestion pipeline (`docs/superpowers/specs/2026-06-16-file-ingestion-pipeline-design.md`) — becomes SP0's data-integration core.
- **Deploy:** Railway single service (API+SPA), deploy via GitHub push to `main` (`railway up` fails for this project); PostGIS.

**Reuse explicitly:** auth/RBAC/tenant, audit, orgs/users admin, MapLibre GIS base, the entire UI design system + theming, the 7 preview module UIs (become real views on SP1 data), the ingestion spec.

## 2. Gap analysis (31 modules → status)

| Blueprint module | Status today | Target SP |
|---|---|---|
| Autenticación y Seguridad | 🟢 have (JWT/RBAC/tenant) — extend with territory scope | SP0 |
| Administración del Sistema | 🟢 have (orgs/users) — extend: campañas, catálogos, config electoral | SP0 |
| Multi-Campaña / Multi-Tenant | 🟡 tenant ✓, **campaign/election missing** | SP0 |
| Gestión Territorial | 🟡 estado+municipio only; **distrito/sección/colonia/manzana/casilla missing** | SP0 |
| Integración de Datos | 📄 specced, not built | SP0 |
| Calidad y Gobernanza de Datos | 🔴 new | SP0 |
| Auditoría Legal y Protección de Datos | 🔴 new (gates PII) | SP0 |
| Notificaciones | 🔴 new (shared service) | SP0 |
| GIS / Mapa Electoral | 🟡 base map+areas; layers/heatmaps/casillas/rutas/zonas new | SP1 |
| Histórico Electoral | 🟡 preview (resultados) | SP1 |
| Demográfico | 🟡 preview | SP1 |
| Socioeconómico | 🟡 preview (economia/índice) | SP1 |
| Dashboard Ejecutivo | 🟡 base; real KPIs new | SP1 |
| Reportes | 🟢 base; territorial/PDF/PPTX exports extend | SP1 |
| Encuestas | 🔴 new | SP2 |
| CRM Ciudadano | 🔴 new (PII) | SP2 |
| Estructura Electoral | 🔴 new (drives territory RBAC) | SP2 |
| Operación de Campo | 🔴 new | SP2 |
| App Móvil de Campo | 🔴 new | SP3 |
| Segmentación Electoral | 🔴 new | SP4 |
| Comunicación Política | 🔴 new | SP4 |
| Demandas Ciudadanas | 🔴 new | SP4 |
| Eventos Territoriales | 🔴 new | SP4 |
| Movilización Electoral | 🔴 new | SP4 |
| Jornada Electoral / War Room | 🔴 new (real-time) | SP5 |
| Incidencias Electorales | 🔴 new | SP5 |
| Inteligencia Competitiva | 🔴 new | SP5 |
| Modelos Predictivos | 🔴 new | SP6 |
| Scoring Electoral | 🔴 new | SP6 |
| Asistente IA Electoral | 🟡 preview (frontend-only, parked) | SP6 |

Net: today ≈ the intelligence/reference slice of Phase 1; the program is ~5–10× current scope, with the operational/real-time/mobile half being entirely new and architecturally distinct.

## 3. Canonical data model (the spine)

Every domain entity carries `tenant_id` (FK Organization) and, where campaign-scoped, `campaign_id`.

### 3.1 Container: Tenant → Campaign/Election
- **`Organization`** (exists) = tenant/operator.
- **`Campaign`** (new): `{ id, tenant_id, name, election_type (federal|local|municipal|…), election_date, geography_scope (root territory ids), status, license_tier }`. The missing container — operational records scope to a campaign.
- **`Election`/`ElectionType` catalog** (new): describes the contest (cargo, year, ámbito) for both historical results and the active campaign.

### 3.2 Spine: Territory hierarchy
Expand `ElectoralArea` into a self-referential hierarchy:
- Add `parent_id` (self-FK) and extend `AreaLevel`: `nation, estado, distrito_federal, distrito_local, municipio, seccion, colonia, manzana, casilla`.
- **The hierarchy is a DAG, not a strict tree:** a `seccion` rolls up to a municipio AND a distrito_federal AND a distrito_local (different aggregations). Model cross-level membership via a `TerritoryMembership` link table (`area_id, ancestor_id, relation`) OR redundant FK columns on `seccion` (`municipio_id, distrito_federal_id, distrito_local_id`). Decision deferred to SP0 spec; **`seccion` is the canonical join key** for all facts; `casilla` belongs to a `seccion`.
- Geometry stays on the area (PostGIS); reuse existing server-side simplification.

### 3.3 Reference facts (read-mostly, batch-ingested) — SP1
- `ElectionResult` (tidy: row per territory+contest+party/coalition/candidate; votes; derived participación/abstención/margen).
- `CensusMetric` (tidy: row per territory+indicator — población, edad, género, hogares, viviendas, escolaridad, ocupación, densidad).
- `SocioMetric` (tidy: row per territory+indicator — marginación, rezago, pobreza, ingreso, servicios, salud, empleo, actividad económica).

### 3.4 Operational facts (transactional, multi-user, mobile/offline, territory-RBAC) — SP2/SP3/SP4/SP5
- `Citizen` (CRM core, PII: nombre, contacto, clave de elector opcional, domicilio→geocoded→seccion; tipo: simpatizante|indeciso|opositor|promotor|líder). **Requires consent record (SP0 legal).**
- `ContactEvent` (historial de contacto, canal, resultado).
- `StructureMember` (coordinador|responsable|representante de casilla|promotor|brigadista; FK user?, FK assigned territory). **Drives territory RBAC.**
- `Survey` / `SurveyQuestion` / `SurveyResponse` (geolocated, validated, real-time aggregation).
- `FieldTask` / `Visit` (asignación, ruta, check-in/out, evidencia foto, productividad).
- `MobilizationRecord` (votante comprometido, confirmación, transporte, ruta, avance por hora).
- `Incident` (registro, evidencia multimedia, ubicación, clasificación jurídica, flujo, expediente, escalamiento).
- `Event` (agenda, territorio, asistentes, evidencia, evaluación).
- `Demand` (problemática ciudadana, tema, geolocalización, prioridad, compromiso).

### 3.5 Real-time facts — SP5
- `PollingStationStatus` (apertura, representante confirmado, participación reportada, acta capturada, foto sábana).
- `QuickCount` (conteo rápido interno vs PREP).
- `CriticalAlert`.

### 3.6 Derived/analytical — SP6
- `TerritoryScore` (prioridad, riesgo, competitividad, abstencionismo, movilización, estructura, persuadibilidad — per seccion).
- `Prediction` (proyección votación/participación, escenarios, riesgo/oportunidad por sección, simulación).

## 4. Cross-cutting platform services (built in SP0, consumed everywhere)

1. **Tenancy & licensing:** `(tenant_id, campaign_id)` scoping enforced in the data-access layer; license tier gates feature/module access.
2. **RBAC-by-territory (row-level):** beyond role, a user's `StructureMember` assignment limits the rows they can read/write to their territory subtree. This is the single biggest cross-cutting change vs today's role-only RBAC. Define the enforcement layer (query filter middleware) in SP0.
3. **Data Integration + Quality/Governance:** ingestion (CSV/Excel/GeoJSON/SHP/KML/API), cleaning, normalization, dedupe, geocoding; plus trazabilidad, versionamiento de bases, detección de inconsistencias, semáforo de calidad. Extends the existing ingestion spec.
4. **Legal / Data Protection:** consent capture + storage, data-subject controls, anonymization, retention policies, access auditing, controlled exports, legal expedientes. **Must exist before any PII (Citizen) is stored — gates SP2.** Legally mandatory (citizen PII).
5. **Notifications:** internal alerts, push, email, WhatsApp; subscriptions by risk/coverage thresholds. Shared by SP4/SP5.
6. **Admin & catalogs:** campaigns, electoral config, catálogos (partidos, cargos, niveles), parámetros — extends current orgs/users admin.

## 5. Sub-projects (each → its own spec→plan cycle)

**SP0 — Platform Core (foundation, gates everything).** Campaign/Election entity + scoping; territory hierarchy to seccion/casilla + real cartography/catalog ingest; RBAC-by-territory; data-integration+quality engine; legal/data-protection foundation; notifications; admin/catalogs. Migrations: introduce Alembic baseline here (today uses `create_all`).

**SP1 — Intelligence (reference data) [parallel stream].** Realize the preview modules on real ingested data: Histórico Electoral, Demográfico, Socioeconómico; deep GIS (capas, polígonos, heatmaps, puntos de casilla, rutas, zonas prioritarias); real Dashboard Ejecutivo; Reportes (territorial, por distrito/municipio/sección, PDF/Excel/PPTX).

**SP2 — Operational Core [parallel stream].** CRM Ciudadano, Estructura Electoral (+ territory RBAC wiring), Operación de Campo, Encuestas. Transactional; consumes SP0 legal/consent.

**SP3 — Mobile + Offline Sync [follows SP2, shares its data].** Field app: offline capture, sync engine + conflict resolution, móvil encuestas/registro/check-in/evidencia/incidencias. The sync architecture (last-write-wins vs CRDT vs queue) is decided in its spec; offline-first is the hard constraint.

**SP4 — Engagement & Targeting [after SP1+SP2].** Segmentación (microtargeting, persuadibles, voto duro), Comunicación Política (scripts, argumentarios, narrativas, objeciones), Demandas Ciudadanas, Eventos Territoriales, Movilización Electoral.

**SP5 — War Room / Election Day [before election; needs SP2 structure].** Jornada/War Room (real-time: apertura, representantes, participación, actas, conteo rápido vs PREP, alertas críticas), Incidencias (real-time + expediente), Inteligencia Competitiva (actores, rivales, presencia territorial, narrativas, medios/redes). Streaming/websockets + high election-day reliability.

**SP6 — Predictive & AI [last; needs real data from SP1–SP5].** Modelos Predictivos, Scoring Electoral (per-seccion scores), Asistente IA Electoral (NL queries, insights, anomalías, briefings) — finally wires the parked AI Analyst to a real LLM.

## 6. Sequencing & dependencies

```
SP0 (Platform Core) ──┬──> SP1 (Intelligence) ──────────┐
                      │                                  ├──> SP4 (Engagement) ──> SP6 (Predictive & AI)
                      └──> SP2 (Operational) ──> SP3 ────┘            │
                                     └──────────────> SP5 (War Room) ─┘
```
- **SP0 is the hard gate.** Nothing real ships without the spine + scoping + legal.
- SP1 and SP2 run in parallel (different squads/streams) once SP0's contracts are frozen.
- SP3 follows SP2 (same operational data). SP5 needs SP2's structure (representantes) and runs against the election calendar. SP6 is last.
- **Calendar reality:** SP5 (war room) is date-bound to the election; sequence so it's production-hardened weeks before. SP1/SP2 deliver continuous value pre-election.

## 7. Top program risks (cross-cutting)

1. **PII & legal exposure** — storing citizen data demands consent/retention/anonymization + access audit from the first CRM row. Mitigation: SP0 legal foundation gates SP2; no PII before it.
2. **Multi-tenant data isolation** — a scoping bug leaks one campaign's data to another. Mitigation: enforce `(tenant_id, campaign_id)` + territory filter at the data-access layer (one chokepoint), not per-query; test isolation explicitly.
3. **Territory model correctness** — the seccion DAG (federal/local/municipio overlaps) is easy to get wrong and everything joins on it. Mitigation: nail it in SP0 with real INE catalogs before building on it.
4. **Offline sync conflicts** — field app correctness under flaky connectivity. Mitigation: SP3 dedicated sync design; idempotent ops; conflict policy decided up front.
5. **Election-day reliability** — war room can't fail under peak load on the one day it matters. Mitigation: SP5 load-tested, degradation modes, offline fallbacks.
6. **Scope/throughput** — 7 sub-projects, parallel streams. Mitigation: strict SP boundaries via frozen SP0 contracts; each SP independently shippable.
7. **Data availability** — reference data (results/census) sourcing for SP1 (external APIs are blocked from Railway → file ingestion is the path); operational data depends on the field team's discipline.

## 8. How this program executes (process)

- This master spec is the program contract. It is **not** implemented directly.
- Each SP, in sequence/parallel per §6, enters the normal cycle: `brainstorming → spec (docs/superpowers/specs/) → writing-plans → subagent-driven implementation` with per-task review — the same loop used for the UI sweep and theming.
- SP0's spec is written first and must freeze the canonical model (§3) and cross-cutting contracts (§4) before SP1/SP2 specs start.
- Branch/deploy norms unchanged (feature branch → main → Railway GitHub push).

## 9. Open questions (resolve at each SP's spec, not here)
- Territory DAG representation (link table vs redundant FKs) — SP0.
- Sync strategy (LWW vs CRDT vs op-queue) — SP3.
- Real-time transport (websockets vs SSE vs polling) for war room — SP5.
- LLM provider/wiring for the AI assistant — SP6 (currently parked by user directive).
- License-tier → feature-gate matrix — SP0.

None block writing the SP0 spec next.
