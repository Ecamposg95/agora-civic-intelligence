import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { CellBar } from "../CellBar";
import { StatusPill } from "../StatusPill";
import { Avatar } from "../Avatar";

describe("CellBar", () => {
  it("renders the numeric value with a percent sign", () => {
    const html = renderToStaticMarkup(<CellBar value={92} />);
    expect(html).toContain("92%");
  });

  it("renders the teal fill bar sized to the value", () => {
    const html = renderToStaticMarkup(<CellBar value={40} />);
    expect(html).toContain("bg-teal");
    expect(html).toMatch(/width:\s*40%/);
  });

  it("clamps out-of-range values into 0..100", () => {
    const over = renderToStaticMarkup(<CellBar value={150} />);
    expect(over).toContain("100%");

    const under = renderToStaticMarkup(<CellBar value={-10} />);
    expect(under).toContain("0%");
  });
});

describe("StatusPill", () => {
  it("renders its children text", () => {
    const html = renderToStaticMarkup(<StatusPill kind="ok">Verificado</StatusPill>);
    expect(html).toContain("Verificado");
  });

  it("uses the teal semantic color for kind=ok", () => {
    const html = renderToStaticMarkup(<StatusPill kind="ok">Verificado</StatusPill>);
    expect(html).toContain("text-teal");
  });

  it("uses the amber semantic color for kind=warn", () => {
    const html = renderToStaticMarkup(<StatusPill kind="warn">Pendiente</StatusPill>);
    expect(html).toContain("Pendiente");
    expect(html).toContain("text-amber");
  });

  it("uses the critical semantic color for kind=crit", () => {
    const html = renderToStaticMarkup(<StatusPill kind="crit">Rechazado</StatusPill>);
    expect(html).toContain("Rechazado");
    expect(html).toContain("text-state-critical");
  });

  it("always renders a dot alongside the label (never color-only)", () => {
    const html = renderToStaticMarkup(<StatusPill kind="ok">Verificado</StatusPill>);
    expect(html).toMatch(/rounded-full/);
  });
});

describe("Avatar", () => {
  it("renders the initials", () => {
    const html = renderToStaticMarkup(<Avatar initials="ML" />);
    expect(html).toContain("ML");
  });

  it("defaults to the brand variant", () => {
    const html = renderToStaticMarkup(<Avatar initials="ML" />);
    expect(html).toContain("text-accent");
  });

  it("supports the warm variant", () => {
    const html = renderToStaticMarkup(<Avatar initials="LC" variant="warm" />);
    expect(html).toContain("LC");
    expect(html).toContain("text-warm");
  });
});
