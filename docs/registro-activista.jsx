import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  UserPlus, Trash2, FileSpreadsheet, ShieldCheck, ChevronDown,
  Users, Phone, MapPin, Hash, CreditCard, Pencil, X, Check,
  AlertTriangle, Save, Building2
} from "lucide-react";
import * as XLSX from "xlsx";

/* ----------------------------- estilos --------------------------------- */
const CSS = `
:root{
  --navy:#16243F; --navy-2:#1E3354; --ink:#0F172A; --muted:#64748B;
  --line:#E4E8EF; --bg:#F4F6FA; --surface:#FFFFFF;
  --accent:#1F8A70; --accent-d:#176B57; --accent-soft:#E6F3EF;
  --danger:#C0392B; --danger-soft:#FBEAE8; --amber:#B7791F; --amber-soft:#FBF3E3;
}
*{box-sizing:border-box}
.ra-root{
  font-family:'Inter',system-ui,sans-serif; color:var(--ink);
  background:linear-gradient(180deg,#EEF2F8 0%,var(--bg) 220px,var(--bg) 100%);
  min-height:100vh; padding:0 0 64px;
}
.ra-wrap{max-width:640px; margin:0 auto; padding:0 16px}
.ra-top{
  background:var(--navy); background-image:linear-gradient(135deg,var(--navy) 0%,var(--navy-2) 100%);
  color:#fff; padding:22px 0 24px; border-bottom:3px solid var(--accent);
}
.ra-top .ra-wrap{display:flex; align-items:center; justify-content:space-between; gap:12px}
.ra-title{font-family:'Plus Jakarta Sans',sans-serif; font-weight:700; font-size:19px; letter-spacing:-.01em; line-height:1.15; margin:0}
.ra-sub{font-size:12px; color:#AEBBD2; margin:3px 0 0}
.ra-count{display:flex; flex-direction:column; align-items:center; background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.14); border-radius:12px; padding:8px 14px; min-width:62px}
.ra-count b{font-family:'Plus Jakarta Sans',sans-serif; font-size:24px; line-height:1}
.ra-count span{font-size:10px; color:#AEBBD2; text-transform:uppercase; letter-spacing:.06em; margin-top:2px}

.card{background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:18px; margin-top:16px; box-shadow:0 1px 2px rgba(16,24,40,.04)}
.card-h{display:flex; align-items:center; gap:9px; margin:0 0 4px}
.card-h h2{font-family:'Plus Jakarta Sans',sans-serif; font-size:15px; font-weight:600; margin:0}
.card-h .ic{color:var(--accent); display:flex}
.card-note{font-size:12px; color:var(--muted); margin:0 0 14px}

.grid{display:grid; grid-template-columns:1fr 1fr; gap:12px}
.field{display:flex; flex-direction:column; gap:5px}
.field.full{grid-column:1 / -1}
label{font-size:12px; font-weight:500; color:#3B4658; display:flex; align-items:center; gap:5px}
label .req{color:var(--danger)}
input{
  font-family:inherit; font-size:14px; color:var(--ink); background:#fff;
  border:1.5px solid var(--line); border-radius:10px; padding:11px 12px; width:100%; transition:.15s;
}
input::placeholder{color:#A6B0C0}
input:focus{outline:none; border-color:var(--accent); box-shadow:0 0 0 3px var(--accent-soft)}
input.warn{border-color:var(--amber)}
.hint{font-size:11px; color:var(--muted)}
.hint.warn{color:var(--amber)}

.consent{display:flex; gap:10px; align-items:flex-start; background:var(--accent-soft); border:1px solid #CDE8E0; border-radius:12px; padding:12px; margin-top:14px; cursor:pointer}
.consent input{width:18px; height:18px; margin-top:1px; accent-color:var(--accent); flex:0 0 auto; cursor:pointer}
.consent span{font-size:12px; color:#2A4A40; line-height:1.45}

.btn{font-family:'Plus Jakarta Sans',sans-serif; font-weight:600; font-size:14px; border:none; border-radius:11px; padding:13px 16px; display:flex; align-items:center; justify-content:center; gap:8px; cursor:pointer; transition:.15s; width:100%}
.btn-primary{background:var(--accent); color:#fff; margin-top:14px}
.btn-primary:hover:not(:disabled){background:var(--accent-d)}
.btn-primary:disabled{background:#C7CFDB; cursor:not-allowed}
.btn-ghost{background:#fff; color:var(--muted); border:1.5px solid var(--line); margin-top:10px}
.btn-ghost:hover{border-color:#CBD3DF; color:var(--ink)}

.priv{background:var(--amber-soft); border:1px solid #EBD9B0}
.priv .card-h .ic{color:var(--amber)}
.priv-toggle{background:none; border:none; cursor:pointer; display:flex; align-items:center; gap:6px; color:var(--amber); font-size:12px; font-weight:600; padding:0; margin-top:6px}
.priv-body{font-size:12px; color:#6B5520; line-height:1.55; margin-top:10px}
.chev{transition:.2s}
.chev.open{transform:rotate(180deg)}

.export{display:flex; gap:10px; margin-top:16px}
.export .btn{margin-top:0}
.btn-xls{background:#107C41; color:#fff}
.btn-xls:hover:not(:disabled){background:#0C6A37}
.btn-xls:disabled{background:#C7CFDB; cursor:not-allowed}
.btn-csv{background:#fff; color:var(--navy); border:1.5px solid var(--line)}
.btn-csv:hover:not(:disabled){border-color:var(--accent); color:var(--accent)}

.empty{text-align:center; padding:34px 16px; color:var(--muted)}
.empty .eic{display:inline-flex; padding:14px; background:#fff; border:1px solid var(--line); border-radius:14px; margin-bottom:10px}
.empty p{font-size:13px; margin:0}

.person{display:flex; gap:12px; padding:14px 0; border-top:1px solid var(--line)}
.person:first-of-type{border-top:none}
.p-num{flex:0 0 auto; width:28px; height:28px; border-radius:8px; background:var(--accent-soft); color:var(--accent-d); font-family:'Plus Jakarta Sans',sans-serif; font-weight:700; font-size:12px; display:flex; align-items:center; justify-content:center}
.p-body{flex:1; min-width:0}
.p-name{font-weight:600; font-size:14px; margin:0 0 4px}
.p-meta{display:flex; flex-wrap:wrap; gap:4px 14px; font-size:12px; color:var(--muted)}
.p-meta span{display:inline-flex; align-items:center; gap:4px}
.p-acts{display:flex; gap:4px; flex:0 0 auto}
.icon-btn{background:none; border:none; cursor:pointer; padding:7px; border-radius:8px; color:var(--muted); display:flex}
.icon-btn:hover{background:#F1F4F9; color:var(--ink)}
.icon-btn.del:hover{background:var(--danger-soft); color:var(--danger)}

.list-h{display:flex; align-items:center; justify-content:space-between; margin-bottom:6px}
.editing-badge{font-size:11px; font-weight:600; color:var(--amber); background:var(--amber-soft); border:1px solid #EBD9B0; padding:3px 9px; border-radius:20px; display:inline-flex; align-items:center; gap:5px}

.foot{text-align:center; font-size:11px; color:#9AA6B6; margin-top:26px; line-height:1.6}
.foot button{background:none; border:none; color:var(--danger); font-size:11px; cursor:pointer; text-decoration:underline; padding:0}

@media (max-width:430px){ .grid{grid-template-columns:1fr} .export{flex-direction:column} }
`;

/* --------------------------- almacenamiento ---------------------------- */
const KEY_H = "activista:header";
const KEY_E = "activista:entries";
const hasStore = typeof window !== "undefined" && window.storage;

async function loadKey(key, fallback) {
  if (!hasStore) return fallback;
  try {
    const r = await window.storage.get(key);
    return r && r.value ? JSON.parse(r.value) : fallback;
  } catch { return fallback; }
}
async function saveKey(key, value) {
  if (!hasStore) return;
  try { await window.storage.set(key, JSON.stringify(value)); } catch {}
}

const EMPTY_PERSON = { nombre: "", seccion: "", direccion: "", colonia: "", clave: "", telefono: "", consent: false };
const EMPTY_HEADER = { nombreActivista: "", lider: "", telefono: "", clave: "" };

/* -------------------------------- app ---------------------------------- */
export default function App() {
  const [header, setHeader] = useState(EMPTY_HEADER);
  const [entries, setEntries] = useState([]);
  const [form, setForm] = useState(EMPTY_PERSON);
  const [editId, setEditId] = useState(null);
  const [privOpen, setPrivOpen] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const link1 = document.createElement("link");
    link1.rel = "stylesheet";
    link1.href = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Plus+Jakarta+Sans:wght@600;700&display=swap";
    document.head.appendChild(link1);
    (async () => {
      setHeader(await loadKey(KEY_H, EMPTY_HEADER));
      setEntries(await loadKey(KEY_E, []));
      setReady(true);
    })();
  }, []);

  useEffect(() => { if (ready) saveKey(KEY_H, header); }, [header, ready]);
  useEffect(() => { if (ready) saveKey(KEY_E, entries); }, [entries, ready]);

  const setH = (k, v) => setHeader(p => ({ ...p, [k]: v }));
  const setF = (k, v) => setForm(p => ({ ...p, [k]: v }));

  const claveLen = form.clave.replace(/\s/g, "").length;
  const claveWarn = claveLen > 0 && claveLen !== 18;
  const canSave = form.nombre.trim().length > 1 && form.consent;

  const savePerson = useCallback(() => {
    if (!canSave) return;
    if (editId) {
      setEntries(p => p.map(e => e.id === editId ? { ...form, id: editId, createdAt: e.createdAt } : e));
    } else {
      setEntries(p => [...p, { ...form, id: Date.now() + "" + Math.random().toString(36).slice(2, 6), createdAt: Date.now() }]);
    }
    setForm(EMPTY_PERSON);
    setEditId(null);
  }, [form, canSave, editId]);

  const startEdit = (e) => { setForm({ ...e }); setEditId(e.id); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const cancelEdit = () => { setForm(EMPTY_PERSON); setEditId(null); };
  const remove = (id) => { setEntries(p => p.filter(e => e.id !== id)); if (editId === id) cancelEdit(); };

  const rows = useMemo(() => entries.map((e, i) => ({
    "#": i + 1,
    "Nombre completo": e.nombre,
    "Sección": e.seccion,
    "Dirección": e.direccion,
    "Bo./Col.": e.colonia,
    "Clave de elector": e.clave,
    "Teléfono": e.telefono,
  })), [entries]);

  const dateStr = () => new Date().toISOString().slice(0, 10);

  const exportXlsx = () => {
    const wb = XLSX.utils.book_new();
    const meta = [
      ["Nombre del activista", header.nombreActivista],
      ["Líder", header.lider],
      ["Teléfono", header.telefono],
      ["Clave de elector", header.clave],
      ["Total registrados", entries.length],
      [],
    ];
    const ws = XLSX.utils.aoa_to_sheet(meta);
    XLSX.utils.sheet_add_json(ws, rows, { origin: -1 });
    ws["!cols"] = [{ wch: 5 }, { wch: 26 }, { wch: 10 }, { wch: 30 }, { wch: 18 }, { wch: 20 }, { wch: 14 }];
    XLSX.utils.book_append_sheet(wb, ws, "Activistas");
    XLSX.writeFile(wb, `activistas_${dateStr()}.xlsx`);
  };

  const exportCsv = () => {
    const head = ["#", "Nombre completo", "Sección", "Dirección", "Bo./Col.", "Clave de elector", "Teléfono"];
    const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const lines = [head.map(esc).join(",")].concat(rows.map(r => head.map(h => esc(r[h])).join(",")));
    const blob = new Blob(["\uFEFF" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `activistas_${dateStr()}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  const clearAll = () => {
    if (window.confirm("¿Borrar TODOS los registros capturados? Esta acción no se puede deshacer.")) {
      setEntries([]); cancelEdit();
    }
  };

  return (
    <div className="ra-root">
      <style>{CSS}</style>

      <div className="ra-top">
        <div className="ra-wrap">
          <div>
            <h1 className="ra-title">Registro de Activista</h1>
            <p className="ra-sub">Captura de campaña · en tu dispositivo</p>
          </div>
          <div className="ra-count">
            <b>{entries.length}</b>
            <span>registros</span>
          </div>
        </div>
      </div>

      <div className="ra-wrap">
        {/* Datos del activista */}
        <div className="card">
          <div className="card-h"><span className="ic"><ShieldCheck size={18} /></span><h2>Datos del activista</h2></div>
          <p className="card-note">Se captura una sola vez. Encabeza el formato y el archivo exportado.</p>
          <div className="grid">
            <div className="field full">
              <label>Nombre del activista</label>
              <input value={header.nombreActivista} onChange={e => setH("nombreActivista", e.target.value)} placeholder="Nombre completo" />
            </div>
            <div className="field full">
              <label>Líder</label>
              <input value={header.lider} onChange={e => setH("lider", e.target.value)} placeholder="Nombre del líder" />
            </div>
            <div className="field">
              <label>Teléfono</label>
              <input value={header.telefono} onChange={e => setH("telefono", e.target.value)} placeholder="10 dígitos" inputMode="tel" />
            </div>
            <div className="field">
              <label>Clave de elector</label>
              <input value={header.clave} onChange={e => setH("clave", e.target.value.toUpperCase())} placeholder="INE (18 caracteres)" />
            </div>
          </div>
        </div>

        {/* Aviso de privacidad */}
        <div className="card priv">
          <div className="card-h"><span className="ic"><AlertTriangle size={18} /></span><h2>Aviso de privacidad</h2></div>
          <p className="card-note" style={{ color: "#6B5520" }}>
            La clave de elector y el teléfono son datos personales protegidos. Captúralos solo con consentimiento y úsalos únicamente para fines de la campaña.
          </p>
          <button className="priv-toggle" onClick={() => setPrivOpen(o => !o)}>
            {privOpen ? "Ocultar texto" : "Ver texto completo"}
            <ChevronDown size={14} className={`chev ${privOpen ? "open" : ""}`} />
          </button>
          {privOpen && (
            <p className="priv-body">
              Los datos recabados (nombre, dirección, sección, colonia, clave de elector y teléfono) serán tratados de forma
              confidencial y exclusivamente para las actividades de organización y promoción de la campaña. No se compartirán con
              terceros ajenos a la misma ni se destinarán a un fin distinto. La persona titular puede solicitar en cualquier momento
              que sus datos sean eliminados del registro. El responsable del tratamiento es el activista que recaba la información.
            </p>
          )}
        </div>

        {/* Formulario de captura */}
        <div className="card">
          <div className="card-h" style={{ justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
              <span className="ic"><UserPlus size={18} /></span>
              <h2>{editId ? "Editar persona" : "Agregar persona"}</h2>
            </div>
            {editId && <span className="editing-badge"><Pencil size={11} /> editando</span>}
          </div>
          <div className="grid">
            <div className="field full">
              <label>Nombre completo <span className="req">*</span></label>
              <input value={form.nombre} onChange={e => setF("nombre", e.target.value)} placeholder="Nombre y apellidos" />
            </div>
            <div className="field">
              <label><Hash size={12} /> Sección</label>
              <input value={form.seccion} onChange={e => setF("seccion", e.target.value)} placeholder="Ej. 4129" inputMode="numeric" />
            </div>
            <div className="field">
              <label><Phone size={12} /> Teléfono</label>
              <input value={form.telefono} onChange={e => setF("telefono", e.target.value)} placeholder="10 dígitos" inputMode="tel" />
            </div>
            <div className="field full">
              <label><MapPin size={12} /> Dirección</label>
              <input value={form.direccion} onChange={e => setF("direccion", e.target.value)} placeholder="Calle y número" />
            </div>
            <div className="field">
              <label><Building2 size={12} /> Bo./Col.</label>
              <input value={form.colonia} onChange={e => setF("colonia", e.target.value)} placeholder="Barrio o colonia" />
            </div>
            <div className="field">
              <label><CreditCard size={12} /> Clave de elector</label>
              <input className={claveWarn ? "warn" : ""} value={form.clave}
                onChange={e => setF("clave", e.target.value.toUpperCase())} placeholder="18 caracteres" />
              {claveWarn
                ? <span className="hint warn">Lleva 18 caracteres ({claveLen} capturados)</span>
                : <span className="hint">Opcional · como aparece en la credencial</span>}
            </div>
          </div>

          <label className="consent">
            <input type="checkbox" checked={form.consent} onChange={e => setF("consent", e.target.checked)} />
            <span>La persona dio su consentimiento para registrar sus datos conforme al aviso de privacidad.</span>
          </label>

          <button className="btn btn-primary" disabled={!canSave} onClick={savePerson}>
            {editId ? <><Save size={17} /> Actualizar persona</> : <><Check size={17} /> Guardar en el registro</>}
          </button>
          {editId && <button className="btn btn-ghost" onClick={cancelEdit}><X size={16} /> Cancelar edición</button>}
        </div>

        {/* Lista */}
        <div className="card">
          <div className="list-h">
            <div className="card-h" style={{ margin: 0 }}>
              <span className="ic"><Users size={18} /></span><h2>Personas registradas</h2>
            </div>
          </div>

          {entries.length === 0 ? (
            <div className="empty">
              <span className="eic"><Users size={22} color="#94A3B8" /></span>
              <p>Aún no hay registros. Captura la primera persona arriba.</p>
            </div>
          ) : (
            entries.map((e, i) => (
              <div className="person" key={e.id}>
                <div className="p-num">{i + 1}</div>
                <div className="p-body">
                  <p className="p-name">{e.nombre}</p>
                  <div className="p-meta">
                    {e.seccion && <span><Hash size={11} />Secc. {e.seccion}</span>}
                    {e.telefono && <span><Phone size={11} />{e.telefono}</span>}
                    {e.colonia && <span><Building2 size={11} />{e.colonia}</span>}
                    {e.clave && <span><CreditCard size={11} />{e.clave}</span>}
                  </div>
                </div>
                <div className="p-acts">
                  <button className="icon-btn" onClick={() => startEdit(e)} title="Editar"><Pencil size={16} /></button>
                  <button className="icon-btn del" onClick={() => remove(e.id)} title="Eliminar"><Trash2 size={16} /></button>
                </div>
              </div>
            ))
          )}

          <div className="export">
            <button className="btn btn-xls" disabled={!entries.length} onClick={exportXlsx}>
              <FileSpreadsheet size={17} /> Exportar Excel
            </button>
            <button className="btn btn-csv" disabled={!entries.length} onClick={exportCsv}>
              CSV
            </button>
          </div>
        </div>

        <p className="foot">
          Los datos se guardan solo en este dispositivo.<br />
          {entries.length > 0 && <button onClick={clearAll}>Borrar todos los registros</button>}
        </p>
      </div>
    </div>
  );
}
