import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  ART_SENTINELS,
  CardBackArt,
  artIds,
  namespaceArt,
  rawArtSources,
  stripEditorCruft,
  themedArt,
} from "./backPatterns";
import { importServerManifest } from "./test-manifest";
import type { Sleeve } from "./sleeves";

const artSource = (id: string) => rawArtSources[id];

const hydrate = (id: string): Sleeve => ({
  id,
  label: "Test",
  palette: { ink: "amber", glow: "cyan", paper: "voidDeep" },
  css: { ink: "var(--amber)", glow: "var(--cyan)", paper: "var(--void-deep)" },
});

describe("backPatterns registry", () => {
  it("one art file per server-manifest sleeve, keyed by sleeve id", () => {
    const manifest = new Set(importServerManifest().map((s) => s.id));
    const art = new Set(artIds());
    expect(manifest).toEqual(art);
  });

  it("falls back to the default art for unknown sleeves", () => {
    const { container } = render(<CardBackArt sleeve={hydrate("nope")} />);
    expect(container.querySelector("svg.card-back-art")).toBeTruthy();
  });
});

describe("art source files (web/src/art/sleeves/*.svg)", () => {
  for (const id of artIds()) {
    it(`${id}.svg is editor-guarded`, () => {
      const src = stripEditorCruft(artSource(id));
      expect(src).toContain('viewBox="0 0 90 120"');
      expect(src).toContain("<svg"); // single root svg element
      /* palette discipline: only the three sentinels may appear */
      const hexes = src.match(/#[0-9a-fA-F]{3,8}\b/g) ?? [];
      const allowed = new Set(Object.values(ART_SENTINELS).flatMap((h) =>
        [h.toLowerCase(), h.toUpperCase()]));
      for (const hex of hexes) {
        expect(allowed.has(hex)).toBe(true);
      }
      /* no scripts, handlers, external refs, raster, or scoped css */
      expect(src).not.toMatch(/<script/i);
      expect(src).not.toMatch(/\son[a-z]+\s*=/i);
      expect(src).not.toMatch(/<image/i);
      expect(src).not.toMatch(/href="(?!#)/);
      expect(src).not.toMatch(/<style/i);
      expect(src).not.toMatch(/\sclass="/);
    });
  }
});

describe("runtime art pipeline", () => {
  it("maps sentinel hexes to the sleeve theme channels", () => {
    for (const id of artIds()) {
      const themed = themedArt(id);
      expect(themed.length).toBeGreaterThan(0);
      expect(themed).not.toContain(ART_SENTINELS.ink);
      expect(themed).not.toContain(ART_SENTINELS.glow);
      expect(themed).not.toContain(ART_SENTINELS.paper);
      if (themed.includes("fill") || themed.includes("stroke")) {
        expect(themed).toMatch(/var\(--sleeve-(ink|glow|paper)\)/);
      }
    }
  });

  it("normalizes font-family to the theme mono face", () => {
    for (const id of artIds()) {
      const themed = themedArt(id);
      for (const m of themed.matchAll(/font-family[=:]["']?([^"';}]*)/g)) {
        expect(m[1]).toBe("var(--font-mono)");
      }
    }
  });

  it("namespaces ids and refs per card instance", () => {
    const themed = themedArt("mixtape");
    const a = namespaceArt(themed, "cbA");
    const b = namespaceArt(themed, "cbB");
    expect(a).toContain('id="cbA-mt"');
    expect(a).toContain("url(#cbA-mt)");
    expect(b).toContain('id="cbB-mt"');
    expect(a.includes('id="cbB-mt"')).toBe(false);
  });

  it("never collides when the same sleeve renders twice", () => {
    const s = hydrate("mixtape");
    const { container } = render(<CardBackArt sleeve={s} />);
    const second = document.createElement("div");
    const { container: c2 } = render(<CardBackArt sleeve={s} />, {
      container: second,
    });
    for (const c of [container, c2]) {
      const svg = c.querySelector("svg.card-back-art") as unknown as SVGSVGElement;
      expect(svg).toBeTruthy();
    }
    const one = container.querySelector("svg.card-back-art")!.outerHTML;
    const two = c2.querySelector("svg.card-back-art")!.outerHTML;
    expect(one).not.toBe(two); // unique useId → ids differ
  });
});
