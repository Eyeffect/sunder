import type { ReactElement } from "react";

/** Hand-tuned geometry for the old sleeve emblems. Drawing them as SVG
  instead of relying on font fallbacks keeps every icon optically centred
  and identical across platforms (the manifest glyph stays as the fallback). */
const SHAPES: Record<string, ReactElement> = {
  frequency: (
    <>
      <circle cx="12" cy="12" r="6.75" fill="none" stroke="currentColor" strokeWidth="2" />
      <circle cx="12" cy="12" r="2.5" fill="currentColor" />
    </>
  ),
  neon: (
    <>
      <path d="M5 9c2.3-2.5 4.7-2.5 7 0s4.7 2.5 7 0" fill="none" stroke="currentColor"
        strokeWidth="2" strokeLinecap="round" />
      <path d="M5 15c2.3-2.5 4.7-2.5 7 0s4.7 2.5 7 0" fill="none" stroke="currentColor"
        strokeWidth="2" strokeLinecap="round" />
    </>
  ),
  cinder: (
    <path d="M13.5 2.5 6 13h5.5L10.5 21.5 18 11h-5.5z" fill="currentColor" />
  ),
  driftglass: (
    <>
      <circle cx="12" cy="12" r="6.75" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M9.25 8.5v7M12 7.5v9M14.75 8.5v7" stroke="currentColor" strokeWidth="1.5"
        strokeLinecap="round" />
    </>
  ),
  spool: (
    <>
      <circle cx="12" cy="12" r="6.75" fill="none" stroke="currentColor" strokeWidth="2" />
      <circle cx="12" cy="12" r="2.5" fill="none" stroke="currentColor" strokeWidth="2" />
    </>
  ),
  spore: (
    <path d="M12 4v16M4 12h16M6.35 6.35l11.3 11.3M17.65 6.35 6.35 17.65" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  ),
  mixtape: (
    <>
      <rect x="4" y="5" width="16" height="14" rx="1" fill="none" stroke="currentColor"
        strokeWidth="2" />
      <path d="M7 9.5h10M7 14.5h10" stroke="currentColor" strokeWidth="1.5"
        strokeLinecap="round" />
    </>
  ),
  vhs: (
    <path d="M6 4.5 18 12 6 19.5z" fill="currentColor" />
  ),
  topo: (
    <>
      <path d="M12 4 20.5 19.5H3.5z" fill="none" stroke="currentColor" strokeWidth="2"
        strokeLinejoin="round" />
      <circle cx="12" cy="14.5" r="1.5" fill="currentColor" />
    </>
  ),
  callsign: (
    <path d="M9.25 4v16M14.75 4v16" stroke="currentColor" strokeWidth="2.4"
      strokeLinecap="square" />
  ),
};

export function AvatarGlyph({
  id,
  glyph,
  className,
}: {
  id?: string;
  glyph?: string;
  className?: string;
}) {
  const shape = id ? SHAPES[id] : undefined;
  if (!shape) {
    return (
      <span className={className} aria-hidden="true">
        {glyph ?? "◉"}
      </span>
    );
  }
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {shape}
    </svg>
  );
}
