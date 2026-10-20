import { describe, expect, it } from "vitest";
import {
  allSleeves,
  setSleeves,
  sleeveOf,
  type SleeveDef,
} from "./sleeves";

const defs: SleeveDef[] = [
  { id: "alpha", label: "Alpha", pattern: "starburst",
    palette: { ink: "amber", glow: "cinder", paper: "panel" }, emblem: "A" },
  { id: "beta", label: "Beta", pattern: "wavelength",
    palette: { ink: "cyan", glow: "green", paper: "voidDeep" } },
];

describe("sleeve registry", () => {
  it("resolves channels to CSS variables", () => {
    setSleeves(defs);
    const s = sleeveOf("alpha");
    expect(s.css.ink).toBe("var(--amber)");
    expect(s.css.glow).toBe("var(--cinder2)");
    expect(s.css.paper).toBe("var(--panel)");
  });

  it("falls back to default sleeve for unknown ids", () => {
    expect(sleeveOf("nope").id).toBe("default");
    expect(sleeveOf("nope").css.ink).toMatch(/^var\(--/);
  });

  it("keeps the fallback manifest on empty sync", () => {
    setSleeves(null);
    expect(allSleeves().length).toBeGreaterThanOrEqual(3);
    setSleeves([]);
    expect(sleeveOf("ember").id).toBe("ember");
  });

  it("syncs the server manifest", () => {
    setSleeves(defs);
    expect(sleeveOf("beta").pattern).toBe("wavelength");
  });
});
