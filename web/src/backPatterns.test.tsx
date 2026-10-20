import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CardBackArt, patternNames } from "./backPatterns";
import { importServerManifest, manifestPatterns } from "./test-manifest";
import type { Sleeve } from "./sleeves";

/** render every registered pattern — missing Sleeve components crash here */
describe("backPatterns", () => {
  for (const pattern of patternNames()) {
    it(`renders the ${pattern} pattern`, () => {
      const s: Sleeve = {
        id: `t-${pattern}`,
        label: "Test",
        pattern,
        palette: { ink: "amber", glow: "cyan", paper: "voidDeep" },
        css: {
          ink: "var(--amber)",
          glow: "var(--cyan)",
          paper: "var(--void-deep)",
        },
      };
      const { container } = render(<CardBackArt sleeve={s} />);
      expect(container.querySelector("svg.card-back-art")).toBeTruthy();
    });
  }

  for (const s of importServerManifest()) {
    it(`sleeve "${s.id}" references a shipped pattern`, () => {
      expect(patternNames()).toContain(s.pattern);
      expect(s.css).toBeTruthy();
    });
  }

  it("the manifest pattern catalog matches the shipped pattern library", () => {
    expect(manifestPatterns().sort()).toEqual([...patternNames()].sort());
  });
});
