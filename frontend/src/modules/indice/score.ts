// frontend/src/modules/indice/score.ts
//
// SAMPLE composite "Índice Cívico-Territorial".
//
// IMPORTANT (honesty): territory identities are REAL (our own cartography),
// but the composite index and every sub-dimension below are DETERMINISTIC
// SAMPLE values derived from `sampleMetric(id)`. There is no real composite
// source yet — these numbers are illustrative and must always be labelled as
// "muestra" in the UI.

import { sampleMetric } from "@/types/maps";

/** A labelled sub-dimension of the sample composite index. */
export interface Dimension {
  /** Stable key, used for chart series / colors. */
  key: "participacion" | "cobertura" | "socioeconomico";
  /** Human label (Spanish). */
  label: string;
  /** Brand color for charts. */
  color: string;
  /** Weight in the composite (sums to 1 across dimensions). */
  weight: number;
}

/** The three sample sub-dimensions and their composite weights. */
export const DIMENSIONS: readonly Dimension[] = [
  {
    key: "participacion",
    label: "Participación cívica",
    color: "#22d3ee",
    weight: 0.4,
  },
  {
    key: "cobertura",
    label: "Cobertura territorial",
    color: "#2dd4bf",
    weight: 0.3,
  },
  {
    key: "socioeconomico",
    label: "Contexto socioeconómico",
    color: "#f5b53d",
    weight: 0.3,
  },
];

/** Per-dimension sample scores in [0,1] for a given area id. */
export type DimensionScores = Record<Dimension["key"], number>;

/** A territory enriched with its sample index + sub-dimensions. */
export interface ScoredArea {
  id: string;
  name: string;
  code: string | null;
  level: string;
  /** Composite sample index in [0,1]. */
  index: number;
  /** Sample sub-dimension scores in [0,1]. */
  dimensions: DimensionScores;
}

const clamp01 = (n: number): number => Math.max(0, Math.min(1, n));

/**
 * Derive a second deterministic pseudo-value from an id + salt so the three
 * sub-dimensions differ from each other (and from the base `sampleMetric`)
 * while staying fully deterministic. Returns a value in [0,1].
 */
function variant(id: string, salt: number): number {
  let h = salt >>> 0;
  for (let i = 0; i < id.length; i++) {
    h = (h * 33 + id.charCodeAt(i)) >>> 0;
  }
  return (h % 1000) / 1000;
}

/**
 * Compute the SAMPLE sub-dimension scores for an area. Anchored on
 * `sampleMetric(id)` so it stays consistent with the rest of the platform,
 * then spread across the three labelled dimensions deterministically.
 */
export function dimensionScores(id: string): DimensionScores {
  const base = sampleMetric(id); // 0.45–0.90, deterministic
  return {
    participacion: clamp01(base),
    cobertura: clamp01(0.35 + variant(id, 101) * 0.6),
    socioeconomico: clamp01(0.3 + variant(id, 211) * 0.65),
  };
}

/** Weighted composite of the sample sub-dimensions, in [0,1]. */
export function compositeIndex(scores: DimensionScores): number {
  const total = DIMENSIONS.reduce(
    (acc, d) => acc + scores[d.key] * d.weight,
    0,
  );
  return clamp01(total);
}

/** Build a fully scored area from its real identity fields. */
export function scoreArea(area: {
  id: string;
  name: string;
  code: string | null;
  level: string;
}): ScoredArea {
  const dimensions = dimensionScores(area.id);
  return {
    id: area.id,
    name: area.name,
    code: area.code,
    level: area.level,
    index: compositeIndex(dimensions),
    dimensions,
  };
}

/** National average of the sample composite index across scored areas. */
export function nationalAverage(areas: ScoredArea[]): number {
  if (areas.length === 0) return 0;
  const sum = areas.reduce((acc, a) => acc + a.index, 0);
  return clamp01(sum / areas.length);
}
