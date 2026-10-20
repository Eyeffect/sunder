import { describe, expect, it } from "vitest";
import {
  allSleeves,
  CHANNELS,
  setSleeves,
  sleeveOf,
  type SleeveDef,
} from "./sleeves";
import { importServerManifest } from "./test-manifest";

const defs: SleeveDef[] = [
  { id: "alpha", label: "Alpha",
    palette: { ink: "amber", glow: "cinder", paper: "panel" } },
  { id: "beta", label: "Beta",
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
    expect(sleeveOf("beta").id).toBe("beta");
    expect(sleeveOf("beta").css.ink).toBe("var(--cyan)");
  });

  it("offline fallback ids and channels agree with the server manifest", () => {
    setSleeves(null); // fallback manifest
    const fallback = allSleeves();
    const server = importServerManifest();
    const byId = new Map(server.map((s) => [s.id, s]));
    for (const fb of fallback) {
      const live = byId.get(fb.id);
      expect(live, `${fb.id} missing from server manifest`).toBeTruthy();
      expect(live!.palette).toEqual(fb.palette);
    }
  });

  it("server manifest palettes only use known theme channels", () => {
    const known = new Set(Object.keys(CHANNELS));
    for (const s of importServerManifest()) {
      for (const ch of Object.values(s.palette)) {
        expect(known.has(ch), `${s.id}: unknown channel "${ch}"`).toBe(true);
      }
    }
  });
});
