// frontend/src/modules/banxico/fixtures.ts
// PREVIEW sample data — Banxico SIE API is unreachable from prod.
// Monthly series are illustrative ("muestra"), shaped to mirror a SIE response.

export interface SeriePoint {
  period: string; // "ene", "feb", … (or YYYY-MM in the future)
  value: number;
}

export interface SerieDef {
  /** Banxico SIE series code (real codes documented for the future swap). */
  code: string;
  label: string;
  unit: string;
  /** "percent" => values are 0..1 ratios; "number" => absolute values. */
  valueFormat: "number" | "percent";
  /** Suffix appended to formatted latest value in KPI tiles. */
  suffix?: string;
  points: SeriePoint[];
}

const MESES = ["jul", "ago", "sep", "oct", "nov", "dic", "ene", "feb", "mar", "abr", "may", "jun"];

const series = (raw: number[]): SeriePoint[] =>
  MESES.map((period, i) => ({ period, value: raw[i] }));

/** Keyed by SIE series code. Real codes noted for the future integration. */
export const SERIES: Record<string, SerieDef> = {
  // Tipo de cambio FIX USD/MXN — SIE SF43718
  SF43718: {
    code: "SF43718",
    label: "Tipo de cambio USD/MXN",
    unit: "MXN por USD",
    valueFormat: "number",
    points: series([17.12, 17.34, 18.05, 18.62, 17.88, 17.21, 16.94, 17.05, 16.72, 16.51, 17.38, 18.12]),
  },
  // Inflación anual INPC — SIE SP1
  SP1: {
    code: "SP1",
    label: "Inflación anual (INPC)",
    unit: "variación anual",
    valueFormat: "percent",
    points: series([0.0472, 0.0464, 0.0445, 0.0476, 0.0455, 0.0437, 0.044, 0.0421, 0.0442, 0.0465, 0.0451, 0.0438]),
  },
  // Tasa de interés objetivo — SIE SF61745
  SF61745: {
    code: "SF61745",
    label: "Tasa objetivo Banxico",
    unit: "tasa de referencia",
    valueFormat: "percent",
    points: series([0.1125, 0.1125, 0.1125, 0.11, 0.11, 0.1075, 0.105, 0.105, 0.1025, 0.1, 0.0975, 0.095]),
  },
  // Valor de la UDI — SIE SP68257
  SP68257: {
    code: "SP68257",
    label: "Valor de la UDIS",
    unit: "MXN por UDI",
    valueFormat: "number",
    suffix: " MXN",
    points: series([8.142, 8.176, 8.211, 8.248, 8.279, 8.305, 8.331, 8.358, 8.39, 8.421, 8.452, 8.484]),
  },
};

export const SERIES_ORDER = ["SF43718", "SP1", "SF61745", "SP68257"] as const;
