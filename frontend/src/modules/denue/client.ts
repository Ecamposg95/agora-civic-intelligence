// frontend/src/modules/denue/client.ts
// PREVIEW client for the Unidades Económicas (DENUE) module.
//
// Returns sample fixtures so the UI can be built and reviewed before the real
// data source is wired. To plug real data later, swap the body of
// getUnidades() for an INEGI DENUE call, e.g.:
//
//   const TOKEN = import.meta.env.VITE_INEGI_TOKEN;
//   // Buscar por área (lat,lng,radio en metros):
//   const res = await fetch(
//     `https://www.inegi.org.mx/app/api/denue/v1/consulta/Buscar/todos/${lat},${lng}/${radio}/${TOKEN}`,
//   );
//   // ...aggregate the DENUE establishment records into the DenueData shape.
//
// The DenueData shape (see fixtures.ts) is the contract the page renders
// against, so a real adapter only needs to produce that shape.

import { DENUE_DATA, type DenueData } from "./fixtures";

/** Returns economic-unit data. PREVIEW: resolves sample fixtures. */
export async function getUnidades(): Promise<DenueData> {
  return DENUE_DATA;
}
