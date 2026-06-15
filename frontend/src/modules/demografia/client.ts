// frontend/src/modules/demografia/client.ts
// PREVIEW client for the Demografía & Censo module.
//
// Returns sample fixtures so the UI can be built and reviewed before the real
// data source is wired. To plug real data later, swap the body of
// getDemografia() for an INEGI call, e.g.:
//
//   const TOKEN = import.meta.env.VITE_INEGI_TOKEN;
//   const res = await fetch(
//     `https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/<ids>/es/0700/false/BISE/2.0/${TOKEN}?type=json`,
//   );
//   // ...map the INEGI BISE/Censo response into the DemografiaData shape.
//
// The DemografiaData shape (see fixtures.ts) is the contract the page renders
// against, so a real adapter only needs to produce that shape.

import { DEMOGRAFIA_DATA, type DemografiaData } from "./fixtures";

/** Returns demographic/census data. PREVIEW: resolves sample fixtures. */
export async function getDemografia(): Promise<DemografiaData> {
  return DEMOGRAFIA_DATA;
}
