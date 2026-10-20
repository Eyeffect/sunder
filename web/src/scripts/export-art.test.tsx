/** One-off exporter: renders every registered pattern to a plain SVG file
  (90×120 viewBox) with the palette sentinels substituted, for hand editing
  in Inkscape. Run: `yarn vitest run web/src/scripts/export-art.test.tsx`.
  Delete after the migration lands. */
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import { it } from "vitest";
import { render } from "@testing-library/react";
import { CardBackArt } from "../backPatterns";
import { importServerManifest } from "../test-manifest";
import type { Sleeve } from "../sleeves";

const SENTINELS = {
  ink: "#ffb545",
  glow: "#5ff2e0",
  paper: "#030304",
};

it("exports every manifest sleeve to an editable svg", () => {
  const out = dirname(dirname(join(import.meta.dirname, "placeholder")));
  const dir = join(out, "art", "sleeves");
  mkdirSync(dir, { recursive: true });
  const sleeves = importServerManifest();
  const files: string[] = [];
  for (const def of sleeves) {
    const s: Sleeve = {
      id: def.id,
      label: def.label,
      pattern: def.pattern,
      palette: def.palette,
      emblem: def.emblem,
      css: SENTINELS,
    };
    const { container } = render(createElement(CardBackArt, { sleeve: s }));
    const svg = container.querySelector("svg.card-back-art") as SVGSVGElement;
    /* interior only: every pattern is one wrapping <g>; chrome (no <g>) trails */
    let inner = svg.innerHTML.match(/<g[\s\S]*<\/g>/)?.[0] ?? "";
    /* strip the React useId suffix from defs ids (e.g. mt-cbr8 -> mt) */
    const tail = inner.match(/-[a-z0-9]+(?=")/)?.[0];
    if (tail) inner = inner.split(tail).join("");
    inner = inner.replace(/></g, ">\n<");
    files.push(def.id);
    writeFileSync(
      join(dir, `${def.id}.svg`),
      [
        `<?xml version="1.0" encoding="UTF-8"?>`,
        `<!-- SUNDER card-back art — sleeve "${def.id}".`,
        `     Paint ONLY with these palette swatches (they are remapped at runtime):`,
        `       ink   ${SENTINELS.ink}  -> var(--sleeve-ink)`,
        `       glow  ${SENTINELS.glow}  -> var(--sleeve-glow)`,
        `       paper ${SENTINELS.paper}  -> var(--sleeve-paper)`,
        `     Keep the 90x120 viewBox. Save as Plain SVG. -->`,
        `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 90 120">`,
        inner,
        `</svg>`,
        ``,
      ].join("\n"),
    );
  }
  expect(files.length).toBeGreaterThan(0);
});
