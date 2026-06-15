// frontend/src/modules/padron/fixtures.ts
export interface AgeBand { band: string; hombres: number; mujeres: number; }
export interface EntityPadron { entity: string; padron: number; }

export const SUMMARY = { padron: 98_500_000, listaNominal: 97_800_000, cobertura: 0.964, edadMediana: 39 };

export const AGE_BANDS: AgeBand[] = [
  { band: "18–24", hombres: 6.1, mujeres: 6.0 },
  { band: "25–34", hombres: 9.4, mujeres: 9.7 },
  { band: "35–44", hombres: 8.2, mujeres: 8.6 },
  { band: "45–54", hombres: 6.7, mujeres: 7.1 },
  { band: "55–64", hombres: 4.9, mujeres: 5.3 },
  { band: "65+", hombres: 4.1, mujeres: 5.0 },
];

export const TOP_ENTITIES: EntityPadron[] = [
  { entity: "Estado de México", padron: 12_900_000 },
  { entity: "Ciudad de México", padron: 7_700_000 },
  { entity: "Jalisco", padron: 6_300_000 },
  { entity: "Veracruz", padron: 5_900_000 },
  { entity: "Puebla", padron: 4_700_000 },
];
