import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { SectionHeading } from "../SectionHeading";

describe("SectionHeading", () => {
  it("renders title and note", () => {
    const html = renderToStaticMarkup(
      <SectionHeading title="Casos" note="hoy" />
    );

    expect(html).toContain("Casos");
    expect(html).toContain("hoy");
  });

  it("renders with eyebrow, title, and note", () => {
    const html = renderToStaticMarkup(
      <SectionHeading eyebrow="Estado" title="Resumen" note="actualizado" />
    );

    expect(html).toContain("Estado");
    expect(html).toContain("Resumen");
    expect(html).toContain("actualizado");
  });

  it("renders title without note", () => {
    const html = renderToStaticMarkup(
      <SectionHeading title="Registro" />
    );

    expect(html).toContain("Registro");
  });

  it("includes warm accent indicator", () => {
    const html = renderToStaticMarkup(
      <SectionHeading title="Casos" />
    );

    // Should have the warm color (--c-warm) accent dot
    expect(html).toContain("bg-warm");
    // Verify the accent dot element exists
    expect(html).toContain("h-2 w-2");
  });
});
