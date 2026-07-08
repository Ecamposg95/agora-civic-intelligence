import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { AreaTrend } from "../AreaTrend";

describe("AreaTrend", () => {
  it("renders an svg with an accessible label", () => {
    const html = renderToStaticMarkup(
      <AreaTrend points={[{ x: "S1", y: 10 }, { x: "S2", y: 20 }]} />,
    );
    expect(html).toMatch(/<svg[^>]*role="img"/);
    expect(html).toMatch(/aria-label="[^"]*20[^"]*"/);
  });

  it("renders an emphasized endpoint and x-axis labels", () => {
    const html = renderToStaticMarkup(
      <AreaTrend points={[{ x: "Ene", y: 5 }, { x: "Feb", y: 15 }, { x: "Mar", y: 30 }]} />,
    );
    expect(html).toContain("Ene");
    expect(html).toContain("Mar");
    expect(html).toMatch(/<circle[^>]*r="5"/);
  });

  it("handles a single point without dividing by zero", () => {
    const html = renderToStaticMarkup(<AreaTrend points={[{ x: "S1", y: 7 }]} />);
    expect(html).toMatch(/<svg[^>]*role="img"/);
  });
});
