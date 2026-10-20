/** SUNDER — station profile icons (separate from sleeve picks).

  The manifest lives server-side in `sunder/cards/avatars.json`, served at
  `/api/avatars` and validated on WS `set_avatar`. The glyph is tinted with
  the station's sleeve ink, so the icon recolours when the sleeve changes.
*/

export const AVATAR_KEY = "sunder-avatar";
export const DEFAULT_AVATAR = "frequency";

export interface AvatarDef {
  id: string;
  label: string;
  glyph: string;
}

/** Offline/boot fallback mirroring the server manifest. */
export const FALLBACK_AVATARS: AvatarDef[] = [
  { id: "frequency", label: "Frequency", glyph: "◉" },
  { id: "neon", label: "Neon", glyph: "≈" },
  { id: "cinder", label: "Cinderworks", glyph: "⌁" },
  { id: "driftglass", label: "Driftglass", glyph: "◍" },
  { id: "spool", label: "Spool", glyph: "◎" },
  { id: "spore", label: "Spore", glyph: "❋" },
  { id: "mixtape", label: "Mixtape", glyph: "▤" },
  { id: "vhs", label: "VHS", glyph: "⏵" },
  { id: "topo", label: "Topo", glyph: "◬" },
  { id: "callsign", label: "Call Sign", glyph: "‖" },
];
