# Registro de Militantes — Diseño

**Fecha:** 2026-07-06
**Estado:** Aprobado (brainstorming)
**Contexto:** Ágora Civic Intelligence · plataforma de captura de activistas (SPA-1..SPA-4) · San Mateo Atenco
**Relacionado:** captura de activistas (`Registro`), territorio + promovidos, RBAC v2, panorama estatal

---

## 1. Objetivo

Agregar el **registro formal de militantes** (integrantes del partido) como una **entidad nueva**, distinta del `Registro`/promovido existente, y darle a **Lucy (coordinadora de campaña)** un tablero para **visualizar la afiliación y tomar decisiones** sobre San Mateo Atenco.

Dos caras del sistema:

1. **Captura de militante** — el **activista** afilia en campo (flujo formal: CURP, credencial INE con foto, firma).
2. **Tablero de afiliación** — **Lucy** visualiza avance, desglose por sección, desempeño por activista y comparativa militantes vs promovidos.

### Decisiones clave (cerradas en brainstorming)

| Tema | Decisión |
|------|----------|
| Qué es "militante" | **Entidad nueva y formal** (integrante del partido; puede además ser activista). Distinta de `Registro`/promovido. |
| Documentos | **Formal completo**: CURP + clave de elector + foto credencial INE (frente/reverso) + **firma digital**. |
| Roles | **Activista captura**; **Lucy visualiza para decidir** (tiene permisos de roles inferiores). |
| Validación | **Híbrido**: cuenta al capturar (`REGISTRADO`); Lucy puede marcar `VALIDADO`/`OBSERVADO`; banderas de calidad automáticas. No bloquea el conteo. |
| Almacenamiento | **Railway Object Storage** (bucket S3-compatible), no imágenes en Postgres. |
| Offline | **Online-first en v1** (fotos de MBs son frágiles en cola IndexedDB). Promovidos/personas siguen offline. Offline con fotos = v2. |
| Folio | Auto-generado por backend (`SMA-<anio>-<secuencia>`, único por campaña); `folio_externo` opcional para cédulas en papel. |

### Fuera de v1 (YAGNI)

- Captura offline de militantes con fotos.
- Presigned PUT directo del móvil al bucket (v1 usa proxy backend).
- Exportación PDF de cédula de afiliación / padrón.
- Firma con huella o validación biométrica.
- Dedup automático que bloquee (solo se marca bandera `posible_duplicado`).

---

## 2. Modelo de datos

Nuevo modelo `Militante` (`backend/app/models/militante.py`), tabla `militantes`, con los mixins de la espina: `UUIDMixin, TenantMixin, CampaignMixin, AuditMixin`. Espeja el patrón de `Registro` pero formal.

### Campos

**Identidad / datos**
- `activista_id` — FK `users.id` (`ondelete=SET NULL`), quién capturó (puede ser el propio militante si se auto-registra).
- `nombre_completo` — `String(255)`, obligatorio.
- `sexo` — `String(1)` (`M`|`F`), nullable.
- `fecha_nacimiento` — `Date`, nullable.
- `seccion` — `String(20)`, nullable.
- `email` — `String(160)`, nullable.
- `telefono` — `String(40)`, nullable.
- Domicilio: `calle_numero` `String(500)`, `colonia` `String(255)`, `cp` `String(10)`, `municipio` `String(120)`, `estado` `String(120)` — todos nullable.
- `es_activista` — `Boolean`, default `False`.
- `estructura` — `String(120)`, nullable.
- `promotor` — `String(160)`, nullable.

**Afiliación**
- `folio` — `String(40)`, único por campaña, auto-generado (`SMA-<anio>-<secuencia>`).
- `folio_externo` — `String(60)`, nullable (folio de cédula en papel).
- `fecha_afiliacion` — `Date`, default = fecha de captura, editable.

**Datos sensibles (cifrados Fernet, patrón de `crypto.py`)**
- `curp_enc` — `LargeBinary`, nullable · `curp_masked` — `String(20)` (ej. `****-XX99`).
- `clave_elector_enc` — `LargeBinary`, nullable · `clave_masked` — `String(20)`.

**Documentos (object keys en el bucket, NO la imagen en DB)**
- `credencial_frente_key` — `String(300)`, nullable.
- `credencial_reverso_key` — `String(300)`, nullable.
- `firma_key` — `String(300)`, nullable.

**Estado híbrido + calidad**
- `estado` — `String(20)` almacenado como NOMBRE en mayúscula (`REGISTRADO`|`VALIDADO`|`OBSERVADO`), default `REGISTRADO`. **Se almacena como `String`, NO como enum de PG** (lección de prod-recovery: evita el dolor de `ALTER TYPE`).
- `validado_por` — FK `users.id`, nullable · `validado_at` — `DateTime(tz)`, nullable.
- `observacion_validacion` — `String(500)`, nullable (motivo si `OBSERVADO`).
- `quality_flags` — `JSON` (SQLite: `Text` con JSON), computado al guardar. Claves booleanas: `falta_curp`, `falta_foto_frente`, `falta_foto_reverso`, `falta_firma`, `clave_incompleta`, `posible_duplicado`.

**Compliance**
- `consentimiento` — `Boolean`, obligatorio.
- `consentimiento_at` — `DateTime(tz)`, nullable.
- `aviso_version` — `String(40)`, nullable (de `PrivacyNotice` activo).
- `manifestacion_voluntad` — `Boolean`, default `False` (la firma capturada la enciende).

**Sello de captura**
- `client_uuid` — `String(64)`, nullable (idempotencia offline futura).
- `lat` / `lng` — `Float`, nullable.

### Índices y constraints

- `Index("ix_militantes_campaign_activista", "campaign_id", "activista_id")`
- `Index("ix_militantes_campaign_seccion", "campaign_id", "seccion")`
- `Index("ix_militantes_campaign_estado", "campaign_id", "estado")`
- `UniqueConstraint("campaign_id", "folio", name="uq_militantes_campaign_folio")`
- `UniqueConstraint("campaign_id", "activista_id", "client_uuid", name="uq_militantes_campaign_activista_client_uuid")`

La detección de duplicados por CURP/clave es una **bandera** (`posible_duplicado`), no un constraint duro: una afiliación no debe romperse por un typo.

### Migración

`backend/app/alembic/versions/0015_militantes.py`, `down_revision: "0014"`, aditiva. Sigue las reglas endurecidas:
- Guardas `_table_exists("militantes")` / `_index_exists(...)` antes de cada DDL (idempotente).
- **Sin enums de PG** (estado = `String`).
- Dialect-safe (SQLite en tests): `JSON`→`Text` fallback si aplica; sin `DO $$`.

---

## 3. Almacenamiento (Railway Object Storage)

### Bucket

- **`agora-uploads`** — provisionado (id `0d05d048-b149-4dcf-9ead-57a358abb4a6`, región `iad`, privado). Reutilizable para otros uploads futuros.
- Railway inyecta al servicio Agora (auto-inject, se cablea en implementación): `BUCKET_ENDPOINT`, `BUCKET_ACCESS_KEY_ID`, `BUCKET_SECRET_ACCESS_KEY`, `BUCKET_NAME`.

### Cliente

Nuevo `backend/app/core/storage.py` (dependencia nueva `boto3`):
- Cliente `boto3` con `endpoint_url=BUCKET_ENDPOINT`, `region_name="us-east-1"` (etiqueta S3), credenciales de env.
- `put_object(key, data: bytes, content_type)` — sube.
- `presigned_get(key, ttl=60)` — URL firmada de vida corta para servir.
- `delete_object(key)` — borra (para retención/ARCO).
- `ensure_storage_ready()` — se llama en el lifespan (fail-fast si faltan las vars, patrón de `ensure_crypto_ready`). **Gate:** si `BUCKET_*` no está seteado, el módulo de militantes se degrada (no rompe el arranque global) — decisión: el fail-fast aplica solo cuando la feature está activa. En v1, con las vars presentes, arranca normal.

### Layout de llaves

```
militantes/{campaign_id}/{militante_id}/frente.jpg
militantes/{campaign_id}/{militante_id}/reverso.jpg
militantes/{campaign_id}/{militante_id}/firma.png
```

### Seguridad de archivos

- Bucket **privado** (Railway no expone URLs públicas).
- El frontend nunca ve credenciales del bucket.
- Servir credenciales INE: **presigned GET de ~60s** generado por el backend tras verificar rol + scope, con `audit_log` `militante.doc.reveal`.
- Upload v1: **proxy backend** (multipart al app → app valida → `put_object`). Fotos comprimidas cliente (~1200px / ~300KB) antes de subir.

---

## 4. API backend

Router `backend/app/routers/militantes.py` + `backend/app/services/militante_service.py`. Schemas en `backend/app/schemas/militante.py`.

### Endpoints

| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| `POST` | `/militantes` | ACTIVISTA+ | Crea militante (JSON). Cifra CURP/clave, genera `folio`, calcula `quality_flags`, escribe consentimiento + `PrivacyAcceptance`. Audita `militante.create`. Devuelve `id` + `folio`. |
| `POST` | `/militantes/{id}/documento` | ACTIVISTA+ (dueño/scope) | Sube UN documento (`tipo=frente\|reverso\|firma`, multipart). Valida tipo/tamaño, `put_object`, actualiza `*_key`, recalcula flags. Audita `militante.doc.upload`. |
| `GET` | `/militantes` | ACTIVISTA+ | Lista **scoped rol∩territorio** (patrón promovidos). Filtros `seccion`, `estado`, `activista`, `flag`, `q`. Paginado `{items,total,limit,offset}`. **Nunca** CURP/clave en claro (solo `*_masked`). |
| `GET` | `/militantes/{id}` | ACTIVISTA+ (scope) | Detalle. Incluye presigned GET de fotos (auditado `militante.doc.reveal`). Sin PII en claro salvo reveal. |
| `PATCH` | `/militantes/{id}/estado` | COORDINADOR/ADMIN/SUPERADMIN | Marca `VALIDADO`/`OBSERVADO` (+motivo). Setea `validado_por`/`validado_at`. Audita `militante.validate`. |
| `GET` | `/militantes/reveal/{id}` | COORDINADOR/ADMIN/SUPERADMIN | Revela CURP/clave en claro. Flujo auditado dedicado (`militante.reveal`), patrón del reveal de clave existente. |
| `GET` | `/militantes/panorama` | COORDINADOR+ | Payload agregado para el tablero de Lucy (§6). Cacheable (estilo intel). |

### Scoping

`_militante_role_scoped(query, ctx)` espeja el patrón de promovidos/registros:
- **ACTIVISTA/CAPTURISTA** → solo sus propios (`activista_id == user.id`).
- **LIDER/COORDINADOR** → su campaña **acotada por territorio** (secciones de su `area_id` vía `territory_service.scope_secciones`).
- **ADMIN** → toda su campaña (bypasa territorio, decisión de producto, igual que promovidos).
- **SUPERADMIN** → todo.

### Folio

`militante_service._next_folio(db, campaign_id)`: prefijo derivado del municipio de la campaña (default `SMA`) + año actual + secuencia por campaña. Generado dentro de la transacción de creación; la unicidad la garantiza el `UniqueConstraint(campaign_id, folio)` (reintenta si colisión).

### Golden rules (respetadas)

`organization_id` del JWT; respuestas Pydantic; envelope `{error:{message,status}}`; paginación estándar; CURP/clave nunca en logs/list/errores, solo en reveal auditado.

---

## 5. Captura de militante (frontend, activista)

Módulo `frontend/src/modules/militantes/`, ruta `/militantes/captura`. Mobile-first. **Wizard de 3 pasos** (una afiliación tiene demasiados campos para un scroll).

**Paso 1 — Identidad:** nombre*, CURP*, clave de elector, fecha de nacimiento, sexo, sección (autocompleta municipio SMA). Validación en vivo: CURP 18 chars + estructura, clave 18.

**Paso 2 — Contacto y domicilio:** calle/número, colonia, CP, teléfono, email, `es_activista` (toggle), estructura/promotor.

**Paso 3 — Documentos y firma:**
- Cámara para **credencial frente** + **reverso**: guía de encuadre, preview, reintentar. Compresión cliente antes de subir.
- **Pad de firma** (canvas táctil → PNG) = manifestación de voluntad.
- Checkbox de consentimiento + aviso de privacidad de afiliación (versión activa de `PrivacyNotice`).

**Confirmar:** `POST /militantes` → recibe `id`+`folio` → sube los 3 documentos con barra de progreso → pantalla de éxito con **folio generado** + "Registrar otro". Banderas de calidad se muestran antes de confirmar (ej. "falta reverso") pero **no bloquean**.

**Online-first:** sin red → mensaje claro "necesitas conexión para afiliar". Sin cola en v1.

API client `frontend/src/api/militantes.ts` (axios `apiClient`, endpoints sin prefijo `/api`).

---

## 6. Tablero de Lucy (frontend, coordinador)

Módulo `frontend/src/modules/militantes/`, ruta `/militantes` (sección "Afiliación"), rol COORDINADOR+. Alimentado por `GET /militantes/panorama` (un payload cacheable). Cuatro bloques:

1. **Avance de afiliación** — KPIs: total militantes, % validados, ritmo 7/30 días + tendencia. Reusa `AnimatedNumber`, `Sparkline`. **Meta:** opcional por campaña (`Campaign.meta_afiliacion`, nullable). Si no está configurada, el bloque muestra el total sin barra de meta; cuando Lucy/admin la fija, aparece "avance vs meta". Sin meta hardcodeada.
2. **Por sección SMA** — 22 secciones: militantes por sección × contexto electoral (`seccion_electoral`: lista nominal, prioridad). Tabla ordenable + mini-coroplético (reusa Map Explorer).
3. **Por activista** — ranking de captura (quién afilia cuánto) + % de calidad (sin banderas). Patrón de tabla existente.
4. **Militantes vs promovidos** — barras comparando afiliados formales vs los 3,502 promovidos por sección: cobertura de la estructura.

**Tabla/detalle para Lucy:** lista scoped con filtros (sección, estado, activista, banderas) + drawer de detalle con fotos (presigned GET auditado) y acción **Validar/Observar**.

**Dirección visual:** mantiene el sistema "Command Center" (negro + cyan/amber). En implementación se invoca **frontend-design** para: KPI de avance como héroe, semántica de color accesible para estados de calidad (registrado/validado/observado), microinteracciones del wizard, y affordances táctiles grandes para cámara/firma (uso en campo, una mano).

---

## 7. Compliance y seguridad

- **CURP y clave**: cifrados Fernet; solo `*_masked` en list/detalle; claro solo en reveal auditado.
- **Fotos INE / firma**: bucket privado; presigned GET de vida corta; cada revelación audita `militante.doc.reveal`.
- **Consentimiento**: cada `POST /militantes` escribe `PrivacyAcceptance` con la versión activa; la firma = manifestación de voluntad.
- **Auditoría**: create, doc.upload, doc.reveal, validate, reveal → `audit_log`.
- **ARCO/retención**: al hard-delete de un militante, `RetentionService` borra también sus objetos del bucket (`delete_object` de las 3 llaves). Se extiende el flujo de retención existente.
- **RBAC**: capturar = ACTIVISTA+; validar/revelar = COORDINADOR+. Enforced en API (`require_roles`).

---

## 8. Testing

**Backend (pytest, SQLite):**
- Modelo/migración: crea/round-trip 0014→0015.
- Crear militante: cifra CURP/clave, genera folio único, calcula flags, escribe consentimiento + audit.
- Scoping: activista ve solo suyos; coordinador acotado por territorio; admin toda campaña; superadmin todo.
- Estado híbrido: cuenta desde `REGISTRADO`; PATCH a `VALIDADO`/`OBSERVADO` audita.
- Reveal: CURP/clave y docs auditados, gate de rol (403 para activista).
- Storage: `storage.py` con cliente fake/mock (moto o stub) — no golpea Railway en tests.
- Golden rules: sin PII en list/errores; envelope; paginación.

**Frontend (build + vitest):**
- `npm run build` verde (type-check).
- Wizard: validación de pasos, compresión de imagen, cálculo de flags cliente.
- API client shape.

---

## 9. Entregables (para el plan de implementación)

1. Modelo `Militante` + migración 0015.
2. `core/storage.py` + dep `boto3` + `ensure_storage_ready` en lifespan; cablear `BUCKET_*` al servicio Agora.
3. `militante_service.py` (crear, scoping, folio, flags, validar, reveal) + schemas.
4. Router `/api/militantes` (7 endpoints).
5. Extender `RetentionService` para borrar objetos del bucket.
6. Frontend: módulo militantes — wizard de captura (3 pasos, cámara, firma) + API client.
7. Frontend: tablero de Lucy (4 bloques) + tabla/detalle + validar/observar.
8. Pase de **frontend-design** sobre el módulo.
9. Tests backend + build/tests frontend.
10. Registrar el módulo en `registry.ts` (rutas + roles + estado activo).
