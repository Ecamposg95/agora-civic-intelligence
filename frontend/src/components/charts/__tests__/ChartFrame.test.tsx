import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { ChartFrame } from "../ChartFrame";

// This project's vitest environment is "node" (no jsdom/testing-library —
// see vitest.config.ts). Assert via server-rendered markup instead of DOM
// queries, matching the convention in CountdownElectoral.test.tsx.
describe("ChartFrame", () => {
  it("shows empty state when empty", () => {
    const html = renderToStaticMarkup(
      <ChartFrame title="Casos" empty>
        <svg />
      </ChartFrame>,
    );
    expect(html).toMatch(/sin datos/i);
  });

  it("renders legend swatches", () => {
    const html = renderToStaticMarkup(
      <ChartFrame title="Casos" legend={[{ label: "Pendiente", color: "var(--chart-1)" }]}>
        <svg />
      </ChartFrame>,
    );
    expect(html).toContain("Pendiente");
  });

  it("renders a loading skeleton", () => {
    const html = renderToStaticMarkup(
      <ChartFrame title="Casos" loading>
        <svg />
      </ChartFrame>,
    );
    expect(html).toMatch(/animate-pulse/);
  });

  it("renders children when not empty/loading", () => {
    const html = renderToStaticMarkup(
      <ChartFrame title="Casos">
        <svg data-testid="chart-body" />
      </ChartFrame>,
    );
    expect(html).toContain("chart-body");
  });

  it("applies className prop to the root element", () => {
    const html = renderToStaticMarkup(
      <ChartFrame title="Casos" className="print:bg-white">
        <svg />
      </ChartFrame>,
    );
    expect(html).toContain("print:bg-white");
  });
});
