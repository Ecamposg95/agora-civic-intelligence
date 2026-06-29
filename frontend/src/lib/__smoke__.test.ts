// Smoke tests — verify vitest + fake-indexeddb polyfill work correctly.
// These stay as a sanity baseline; do not delete.

import "fake-indexeddb/auto";

test("arithmetic sanity", () => {
  expect(1 + 1).toBe(2);
});

test("indexedDB is defined via fake-indexeddb polyfill", () => {
  expect(typeof indexedDB).toBe("object");
  expect(indexedDB).toBeDefined();
});
