// frontend/src/modules/denue/fixtures.ts
// PREVIEW sample data for the Unidades Económicas (DENUE) module.
// Figures are illustrative ("muestra"); real data should come from the INEGI
// DENUE API once a token is wired. See client.ts.

export interface SectorCount {
  /** Economic sector label. */
  sector: string;
  /** Number of economic units in the sector. */
  count: number;
  color: string;
}

export interface SizeBand {
  /** Establishment size band (by number of employees). */
  band: string;
  count: number;
}

export interface SampleUnit {
  id: string;
  name: string;
  sector: string;
  /** Municipality / locality. */
  municipio: string;
  lat: number;
  lng: number;
}

export interface DenueData {
  summary: {
    total: number;
    sectores: number;
    municipios: number;
    /** Share that are micro establishments (0–5 employees). */
    microShare: number;
  };
  sectors: SectorCount[];
  sizeBands: SizeBand[];
  units: SampleUnit[];
}

/** Economic units by sector — muestra. */
export const SECTORS: SectorCount[] = [
  { sector: "Comercio al por menor", count: 2_140_000, color: "#22d3ee" },
  { sector: "Servicios de alojamiento y alimentos", count: 690_000, color: "#f5b53d" },
  { sector: "Industrias manufactureras", count: 612_000, color: "#2dd4bf" },
  { sector: "Otros servicios", count: 540_000, color: "#7c8aa5" },
  { sector: "Comercio al por mayor", count: 318_000, color: "#06b6d4" },
  { sector: "Servicios educativos y de salud", count: 286_000, color: "#f4607a" },
  { sector: "Transportes y comunicaciones", count: 124_000, color: "#8b9bf4" },
];

/** Establishments by size band (employees) — muestra. */
export const SIZE_BANDS: SizeBand[] = [
  { band: "0–5", count: 4_510_000 },
  { band: "6–10", count: 480_000 },
  { band: "11–30", count: 232_000 },
  { band: "31–50", count: 58_000 },
  { band: "51–100", count: 31_000 },
  { band: "101+", count: 19_000 },
];

/** Small list of sample geolocated units (CDMX / EdoMéx area) — muestra. */
export const UNITS: SampleUnit[] = [
  { id: "u-001", name: "Abarrotes La Esperanza", sector: "Comercio al por menor", municipio: "Iztapalapa, CDMX", lat: 19.3574, lng: -99.0594 },
  { id: "u-002", name: "Taquería El Buen Pastor", sector: "Servicios de alojamiento y alimentos", municipio: "Cuauhtémoc, CDMX", lat: 19.4326, lng: -99.1332 },
  { id: "u-003", name: "Refaccionaria Centro", sector: "Comercio al por menor", municipio: "Toluca, Méx.", lat: 19.2826, lng: -99.6557 },
  { id: "u-004", name: "Manufacturas Textiles del Valle", sector: "Industrias manufactureras", municipio: "Naucalpan, Méx.", lat: 19.4785, lng: -99.2396 },
  { id: "u-005", name: "Farmacia San Rafael", sector: "Servicios educativos y de salud", municipio: "Benito Juárez, CDMX", lat: 19.3727, lng: -99.1588 },
  { id: "u-006", name: "Ferretería Industrial Norte", sector: "Comercio al por mayor", municipio: "Tlalnepantla, Méx.", lat: 19.5402, lng: -99.1959 },
  { id: "u-007", name: "Hotel Plaza Reforma", sector: "Servicios de alojamiento y alimentos", municipio: "Cuauhtémoc, CDMX", lat: 19.4274, lng: -99.1677 },
  { id: "u-008", name: "Colegio Bilingüe Las Águilas", sector: "Servicios educativos y de salud", municipio: "Álvaro Obregón, CDMX", lat: 19.3506, lng: -99.2207 },
  { id: "u-009", name: "Transportes Logísticos del Centro", sector: "Transportes y comunicaciones", municipio: "Ecatepec, Méx.", lat: 19.6011, lng: -99.0507 },
  { id: "u-010", name: "Papelería y Servicios Digitales", sector: "Otros servicios", municipio: "Coyoacán, CDMX", lat: 19.3467, lng: -99.1618 },
  { id: "u-011", name: "Distribuidora de Alimentos del Sur", sector: "Comercio al por mayor", municipio: "Tlalpan, CDMX", lat: 19.2939, lng: -99.1626 },
  { id: "u-012", name: "Carpintería y Muebles Roble", sector: "Industrias manufactureras", municipio: "Nezahualcóyotl, Méx.", lat: 19.4003, lng: -99.0145 },
];

export const DENUE_DATA: DenueData = {
  summary: {
    total: 5_330_000,
    sectores: SECTORS.length,
    municipios: 2_469,
    microShare: 0.846,
  },
  sectors: SECTORS,
  sizeBands: SIZE_BANDS,
  units: UNITS,
};
