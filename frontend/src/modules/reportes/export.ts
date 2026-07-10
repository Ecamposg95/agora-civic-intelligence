// frontend/src/modules/reportes/export.ts
import type { ExecutiveDashboard } from "@/api/dashboard";

/** A labelled row destined for the CSV briefing. */
interface CsvRow {
  section: string;
  label: string;
  value: string | number;
}

/** RFC-4180-ish escaping: quote fields containing commas, quotes or newlines. */
function escapeCsv(value: string | number): string {
  const s = String(value);
  if (/[",\n\r]/.test(s)) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

/** YYYY-MM-DD for filenames, derived from a Date. */
export function fileDate(date: Date = new Date()): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/**
 * Serialize the campaign executive briefing (KPIs + breakdowns) into CSV rows.
 * Pure: only real values from the executive-dashboard payload.
 */
export function briefingToCsvRows(dashboard: ExecutiveDashboard): CsvRow[] {
  const rows: CsvRow[] = [];

  // KPI summary
  rows.push({ section: "Resumen", label: "Promovidos — total", value: dashboard.promovidos.total });
  if (dashboard.promovidos.meta != null) {
    rows.push({ section: "Resumen", label: "Promovidos — meta", value: dashboard.promovidos.meta });
  }
  if (dashboard.promovidos.pct != null) {
    rows.push({ section: "Resumen", label: "Promovidos — % de meta", value: dashboard.promovidos.pct });
  }
  rows.push({ section: "Resumen", label: "Afiliados — total", value: dashboard.afiliados.total });
  rows.push({ section: "Resumen", label: "Afiliados — validados", value: dashboard.afiliados.validados });
  if (dashboard.afiliados.meta != null) {
    rows.push({ section: "Resumen", label: "Afiliados — meta", value: dashboard.afiliados.meta });
  }
  rows.push({ section: "Resumen", label: "Casos — total", value: dashboard.casos.total });
  rows.push({ section: "Resumen", label: "Casos — abiertos", value: dashboard.casos.abiertos });
  rows.push({ section: "Resumen", label: "Casos — SLA vencidos", value: dashboard.casos.sla_vencidos });
  rows.push({ section: "Resumen", label: "Cobertura — secciones", value: dashboard.cobertura.secciones });
  rows.push({ section: "Resumen", label: "Cobertura — al día", value: dashboard.cobertura.al_dia });
  rows.push({ section: "Resumen", label: "Cobertura — en riesgo", value: dashboard.cobertura.en_riesgo });
  if (dashboard.cobertura.pct_global != null) {
    rows.push({ section: "Resumen", label: "Cobertura — % global", value: dashboard.cobertura.pct_global });
  }
  if (dashboard.election_date) {
    rows.push({ section: "Resumen", label: "Fecha de elección", value: dashboard.election_date });
  }

  // Weekly capture trend
  for (const p of dashboard.tendencia) {
    rows.push({ section: "Tendencia semanal (promovidos)", label: p.semana, value: p.promovidos });
  }

  // Top secciones by promovidos
  for (const s of dashboard.por_seccion_top) {
    rows.push({ section: "Top secciones por promovidos", label: s.seccion, value: s.promovidos });
  }

  // Casos por estado
  for (const c of dashboard.casos_por_estado) {
    rows.push({ section: "Casos por estado", label: c.estado, value: c.n });
  }

  // Alertas de cobertura (secciones en riesgo)
  for (const a of dashboard.alertas) {
    rows.push({ section: "Secciones en riesgo", label: a.seccion, value: `faltan ${a.faltan}` });
  }

  // Provenance
  rows.push({ section: "Metadatos", label: "Generado por", value: "Atenea Civic Intelligence" });
  rows.push({ section: "Metadatos", label: "Exportado", value: new Date().toISOString() });

  return rows;
}

/** Build the full CSV text (with header) from briefing rows. */
export function rowsToCsv(rows: CsvRow[]): string {
  const header = ["Sección", "Concepto", "Valor"];
  const lines = [header.map(escapeCsv).join(",")];
  for (const r of rows) {
    lines.push([r.section, r.label, r.value].map(escapeCsv).join(","));
  }
  // BOM so Excel reads UTF-8 (accents) correctly.
  return `﻿${lines.join("\r\n")}`;
}

/**
 * Serialize the campaign briefing to CSV and trigger a client-side Blob download.
 * No external dependencies — uses the DOM URL/anchor pattern.
 */
export function downloadCSV(dashboard: ExecutiveDashboard): void {
  const csv = rowsToCsv(briefingToCsvRows(dashboard));
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `Reporte_Campana_${fileDate()}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
