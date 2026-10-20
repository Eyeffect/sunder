import { useId } from "react";
import type { Sleeve } from "./sleeves";

/** SUNDER — card-back art loader.

  Card-back art lives as hand-editable SVG files in `web/src/art/sleeves/`
  (one file per sleeve id, 90×120 viewBox, Inkscape-friendly). Paint with
  the palette sentinels only — this module remaps them to the sleeve's
  live theme channels at runtime and namespaces defs ids per instance so
  multiple backs on one page never collide. */

import artDefault from "./art/sleeves/default.svg?raw";
import artEmber from "./art/sleeves/ember.svg?raw";
import artStatic from "./art/sleeves/static.svg?raw";
import artNeonfreq from "./art/sleeves/neonfreq.svg?raw";
import artCinderworks from "./art/sleeves/cinderworks.svg?raw";
import artDriftglass from "./art/sleeves/driftglass.svg?raw";
import artSpool from "./art/sleeves/spool.svg?raw";
import artSporewake from "./art/sleeves/sporewake.svg?raw";
import artMixtape from "./art/sleeves/mixtape.svg?raw";
import artVhs from "./art/sleeves/vhs.svg?raw";
import artTopo from "./art/sleeves/topo.svg?raw";
import artBarcode from "./art/sleeves/barcode.svg?raw";

const W = 90;
const H = 120;
const CX = W / 2;
const CY = H / 2;

/** Sentinel hexes painted inside the source SVG files; mapped to the
  sleeve's resolved palette channels at import time. */
export const ART_SENTINELS = {
  ink: "#ffb545",
  glow: "#5ff2e0",
  paper: "#030304",
} as const;

const ART: Record<string, string> = {
  default: artDefault,
  ember: artEmber,
  static: artStatic,
  neonfreq: artNeonfreq,
  cinderworks: artCinderworks,
  driftglass: artDriftglass,
  spool: artSpool,
  sporewake: artSporewake,
  mixtape: artMixtape,
  vhs: artVhs,
  topo: artTopo,
  barcode: artBarcode,
};

/** Raw SVG source per sleeve id (as shipped in the bundle — tests drift
  against these exact bytes, so hand edits are guarded at the bundler). */
export const rawArtSources: Record<string, string> = ART;

/** Strip editor cruft and map sentinel colors → theme channels. Cached:
  the output is uid-free and identical for every card using the art. */
const themedCache = new Map<string, string>();

export function themedArt(id: string): string {
  const cached = themedCache.get(id);
  if (cached !== undefined) return cached;
  const src = ART[id] ?? ART.default;
  let out = src
    .replace(/<metadata[\s\S]*?<\/metadata>/g, "")
    .replace(/<(sodipodi|inkscape):namedview[\s\S]*?(\/>|<\/\1:namedview>)/g, "")
    .replace(/\s(?:inkscape|sodipodi):[\w-]+="[^"]*"/g, "");
  /* peel the <svg> wrapper: chrome renders markup inside our own <svg> */
  const open = out.match(/<svg[^>]*>/)?.index;
  if (open !== undefined) {
    const start = open + (out.match(/<svg[^>]*>/)?.[0].length ?? 0);
    const end = out.lastIndexOf("</svg>");
    out = out.slice(start, end > start ? end : undefined);
  }
  for (const [hex, channel] of [
    [ART_SENTINELS.ink, "var(--sleeve-ink)"],
    [ART_SENTINELS.glow, "var(--sleeve-glow)"],
    [ART_SENTINELS.paper, "var(--sleeve-paper)"],
  ] as const) {
    out = out.split(hex).join(channel).split(hex.toUpperCase()).join(channel);
  }
  /* editors may bake a concrete mono font; normalize to the theme face */
  out = out.replace(/font-family="[^"]*"/g, 'font-family="var(--font-mono)"');
  out = out.replace(/font-family:[^;"}']*/g, "font-family:var(--font-mono)");
  themedCache.set(id, out);
  return out;
}

/** Namespace defs ids + references so N card backs on one page never
  share a gradient id (regression guard from the useId pass). */
export function namespaceArt(svg: string, uid: string): string {
  return svg
    .replace(/\bid="([^"]+)"/g, `id="${uid}-$1"`)
    .replace(/url\(#([^)"']+)\)/g, `url(#${uid}-$1)`)
    .replace(/(\s(?:xlink:)?href)="#([^"]+)"/g, `$1="#${uid}-$2"`);
}

export function artIds(): string[] {
  return Object.keys(ART);
}

/** Shared chrome around any art interior. */
export function CardBackArt({ sleeve }: { sleeve: Sleeve }) {
  const rawId = useId();
  const uid = `cb${rawId.replace(/[^a-zA-Z0-9]/g, "")}`;
  const inner = namespaceArt(themedArt(sleeve.id), uid);
  return (
    <svg
      className="card-back-art"
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      <g dangerouslySetInnerHTML={{ __html: inner }} />
      {/* unified chrome */}
      <defs>
        <radialGradient id={`vig-${uid}`} cx="0.5" cy="0.5" r="0.72">
          <stop offset="0.62" stopColor="#000" stopOpacity="0" />
          <stop offset="1" stopColor="#000" stopOpacity="0.5" />
        </radialGradient>
      </defs>
      <rect width={W} height={H} fill={`url(#vig-${uid})`} />
      <rect x="3.5" y="3.5" width={W - 7} height={H - 7} fill="none" stroke={sleeve.css.ink} strokeWidth="2" />
      {[[12, 12], [W - 12, 12], [12, H - 12], [W - 12, H - 12]].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="1.5" fill={sleeve.css.ink} opacity="0.7" />
      ))}
      <circle cx={CX} cy={CY} r="12.5" fill="none" stroke={sleeve.css.ink} strokeWidth="1" opacity="0.3" />
    </svg>
  );
}
