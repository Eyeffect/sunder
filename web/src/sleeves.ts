/** SUNDER — card-back sleeve registry.

  The manifest of sleeves lives server-side in `sunder/cards/sleeves.json`
  (validated by the server on WS `set_sleeve`, served over `/api/sleeves`).
  This module holds a synced copy of that manifest for rendering. Adding a
  new sleeve = one entry in sleeves.json + one art file in
  `web/src/art/sleeves/<id>.svg`.
*/

export interface SleevePalette {
  ink: string;
  glow: string;
  paper: string;
}

export interface SleeveDef {
  id: string;
  label: string;
  palette: { ink: string; glow: string; paper: string };
  plane?: string;
}

/** A manifest sleeve with theme channels resolved to CSS variables. */
export interface Sleeve {
  id: string;
  label: string;
  palette: SleevePalette;
  plane?: string;
  /** concrete CSS color strings for styling hooks */
  css: SleevePalette;
}

/** localStorage key for your own sleeve pick (sent to the server on connect) */
export const SLEEVE_KEY = "sunder-sleeve";

/** theme.css channels referenced by sleeve palettes (exported for the
  manifest drift tests — palettes may only name channels listed here) */
export const CHANNELS: Record<string, string> = {
  amber: "var(--amber)",
  amberDim: "var(--amber-dim)",
  cyan: "var(--cyan)",
  magenta: "var(--magenta)",
  green: "var(--green)",
  cinder: "var(--cinder2)",
  danger: "var(--danger)",
  text: "var(--text)",
  voidDeep: "var(--void-deep)",
  panel: "var(--panel)",
};

/** Offline/boot fallback mirroring the server manifest. */
const FALLBACK: SleeveDef[] = [
  { id: "default", label: "Frequency",
    palette: { ink: "amber", glow: "amber", paper: "voidDeep" } },
  { id: "ember", label: "Ember",
    palette: { ink: "amber", glow: "amber", paper: "voidDeep" } },
  { id: "static", label: "Static",
    palette: { ink: "magenta", glow: "magenta", paper: "voidDeep" } },
];

let manifest: SleeveDef[] = FALLBACK;

function resolve(ch: string): string {
  return CHANNELS[ch] ?? "var(--amber)";
}

/** Resolve a manifest palette channel name (e.g. snapshot `sleeve_ink`). */
export function channelColor(ch?: string): string {
  return CHANNELS[ch ?? "amber"] ?? "var(--amber)";
}

function hydrate(def: SleeveDef): Sleeve {
  return {
    ...def,
    palette: { ink: def.palette.ink, glow: def.palette.glow, paper: def.palette.paper },
    css: {
      ink: resolve(def.palette.ink),
      glow: resolve(def.palette.glow),
      paper: resolve(def.palette.paper),
    },
  };
}

/** Sync the client manifest with `/api/sleeves`. Empty data keeps fallback. */
export function setSleeves(defs: SleeveDef[] | undefined | null): void {
  manifest = Array.isArray(defs) && defs.length > 0 ? defs : FALLBACK;
}

export function allSleeves(): Sleeve[] {
  return manifest.map(hydrate);
}

export function sleeveOf(id: string): Sleeve {
  const found = manifest.find((s) => s.id === id);
  const def = found ?? manifest.find((s) => s.id === "default") ?? FALLBACK[0];
  return hydrate(def);
}

/** Hydrate a raw manifest entry (e.g. straight from /api/sleeves). */
export function sleeveFromDef(def: SleeveDef): Sleeve {
  return hydrate(def);
}
