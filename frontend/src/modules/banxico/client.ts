// frontend/src/modules/banxico/client.ts
import { SERIES, type SerieDef } from "./fixtures";

/**
 * Returns a sample macro-financial series by Banxico SIE code (PREVIEW).
 *
 * The Banxico SIE API (sie.banxico.org.mx) is unreachable from production, so
 * this returns bundled fixtures for now.
 *
 * FUTURE: swap the body for a backend proxy call, e.g.
 *   const res = await fetch(`/api/intel/banxico/series/${code}`);
 *   return (await res.json()) as SerieDef;
 * keeping the SerieDef shape stable so the page does not change. The backend
 * proxy holds the SIE token and maps SIE's { idSerie, datos:[{fecha,dato}] }.
 */
export async function getSeries(code: string): Promise<SerieDef | null> {
  return SERIES[code] ?? null;
}
