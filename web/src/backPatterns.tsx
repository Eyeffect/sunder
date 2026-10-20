import type { ReactNode } from "react";
import type { Sleeve } from "./sleeves";

/** SUNDER — SVG card-back pattern library.

  Every pattern draws inside a shared 90×120 viewBox and receives the
  sleeve's resolved palette so any pattern composes with any colors.
  Shared chrome (rim, rivets, vignette, medallion) is applied around the
  interior so all backs share consistent edges. New pattern style = new
  entry in `PATTERNS`.
*/

export type PatternFn = (s: Sleeve, uid: string) => ReactNode;

const W = 90;
const H = 120;
const CX = W / 2;
const CY = H / 2;

const rings = (r: number[], cx: number, cy: number, stroke: string) =>
  r.map((rad, i) => (
    <circle
      key={i}
      cx={cx}
      cy={cy}
      r={rad}
      fill="none"
      stroke={stroke}
      strokeWidth={i % 2 === 0 ? 1.6 : 0.8}
      opacity={0.26 - i * 0.03}
    />
  ));

const starburstRays = (count: number, cx: number, cy: number, r0: number, r1: number, stroke: string) =>
  Array.from({ length: count }, (_, i) => {
    const a = (i / count) * Math.PI * 2;
    return (
      <line
        key={i}
        x1={cx + Math.cos(a) * r0}
        y1={cy + Math.sin(a) * r0}
        x2={cx + Math.cos(a) * r1}
        y2={cy + Math.sin(a) * r1}
        stroke={stroke}
        strokeWidth={i % 2 ? 1.4 : 0.7}
        opacity={i % 2 ? 0.34 : 0.16}
      />
    );
  });

/** tiny deterministic PRNG so noise layouts are stable */
function mulberry32(seed: number): () => number {
  let t = seed >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

const PATTERNS: Record<string, PatternFn> = {
  wavelength: (s, uid) => (
    <g>
      <rect x="0" y="0" width={W} height={H} fill={s.css.paper} />
      <defs>
        <linearGradient id={`wl-${uid}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={s.css.ink} stopOpacity="0.07" />
          <stop offset="0.85" stopColor={s.css.ink} stopOpacity="0" />
        </linearGradient>
      </defs>
      <rect width={W} height={H} fill={`url(#wl-${uid})`} />
      {rings([10, 19, 28, 37, 46], CX, CY + 4, s.css.ink)}
      <line x1="8" y1={CY + 4} x2={W - 8} y2={CY + 4} stroke={s.css.ink} strokeWidth="0.7" opacity="0.22" strokeDasharray="3 5" />
      <circle cx="16" cy="14" r="2.4" fill={s.css.glow} opacity="0.8" />
      <text x="22" y="18" fontFamily="var(--font-mono)" fontSize="6" fill={s.css.ink} opacity="0.5">
        101.3 FM
      </text>
    </g>
  ),

  starburst: (s, uid) => (
    <g>
      <rect x="0" y="0" width={W} height={H} fill={s.css.paper} />
      <defs>
        <radialGradient id={`sb-${uid}`} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor={s.css.ink} stopOpacity="0.2" />
          <stop offset="1" stopColor={s.css.ink} stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width={W} height={H} fill={`url(#sb-${uid})`} />
      {starburstRays(28, CX, CY, 14, 60, s.css.ink)}
      {rings([14, 22, 34, 50], CX, CY, s.css.ink)}
      <circle cx={CX} cy={CY} r="6" fill="none" stroke={s.css.glow} strokeWidth="1.4" opacity="0.55" />
    </g>
  ),

  staticNoise: (s, uid) => {
    const rnd = mulberry32(1710);
    const cells: ReactNode[] = [];
    for (let y = 0; y < 16; y++) {
      for (let x = 0; x < 12; x++) {
        const n = rnd();
        if (n > 0.36) {
          cells.push(
            <rect
              key={`${x}-${y}`}
              x={(x * W) / 12}
              y={(y * H) / 16}
              width={(W / 12) * (0.4 + rnd() * 0.6)}
              height={(H / 16) * (0.3 + rnd() * 0.5)}
              fill={n > 0.88 ? s.css.glow : s.css.ink}
              opacity={0.05 + rnd() * 0.14}
            />,
          );
        }
      }
    }
    return (
      <g>
        <rect x="0" y="0" width={W} height={H} fill={s.css.paper} />
        {cells}
        <defs>
          <radialGradient id={`sn-${uid}`} cx="0.5" cy="0.42" r="0.55">
            <stop offset="0" stopColor={s.css.ink} stopOpacity="0.14" />
            <stop offset="1" stopColor={s.css.ink} stopOpacity="0" />
          </radialGradient>
        </defs>
        <rect width={W} height={H} fill={`url(#sn-${uid})`} />
        <line x1="0" y1={CY + 7} x2={W} y2={CY + 7} stroke={s.css.ink} strokeWidth="1.2" opacity="0.3" />
        <circle cx={CX} cy={CY} r="7" fill="none" stroke={s.css.glow} strokeWidth="1.2" opacity="0.5" />
      </g>
    );
  },

  circuit: (s, uid) => {
    const trace = (d: string) => (
      <path key={d} d={d} fill="none" stroke={s.css.ink} strokeWidth="1.6" opacity="0.4" strokeLinecap="round" />
    );
    const traces = [
      `M4 16 H30 V38 H58`,
      `M4 104 H22 V76 H40 V52`,
      `M86 20 H62 V44 H44 V72`,
      `M86 98 H70 V78 H54`,
      `M14 6 V30 H44`,
      `M76 112 V92 H58`,
      `M4 60 H20`,
      `M70 60 H86`,
    ];
    const nodes = [
      [30, 16], [58, 38], [22, 104], [40, 52], [62, 44], [54, 72],
      [70, 78], [44, 6], [58, 92], [20, 60], [70, 60],
    ] as const;
    return (
      <g>
        <rect x="0" y="0" width={W} height={H} fill={s.css.paper} />
        {traces.map(trace)}
        <defs>
          <radialGradient id={`ci-${uid}`} cx="0.5" cy="0.5" r="0.55">
            <stop offset="0" stopColor={s.css.ink} stopOpacity="0.12" />
            <stop offset="1" stopColor={s.css.ink} stopOpacity="0" />
          </radialGradient>
        </defs>
        <rect width={W} height={H} fill={`url(#ci-${uid})`} />
        {nodes.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r="2.2" fill="none" stroke={s.css.ink} strokeWidth="1" opacity="0.55" />
        ))}
        <circle cx={CX} cy={CY} r="12" fill="none" stroke={s.css.glow} strokeWidth="1.2" opacity="0.5" />
        <circle cx={CX - 17} cy={CY} r="1.6" fill={s.css.glow} opacity="0.7" />
        <circle cx={CX + 17} cy={CY} r="1.6" fill={s.css.glow} opacity="0.7" />
      </g>
    );
  },

  vinyl: (s, uid) => (
    <g>
      <rect x="0" y="0" width={W} height={H} fill={s.css.paper} />
      {rings([24, 27, 30, 33, 36], CX, CY, s.css.ink)}
      <circle cx={CX} cy={CY} r="40" fill="none" stroke={s.css.ink} strokeWidth="0.7" opacity="0.12" />
      <circle cx={CX} cy={CY} r="42" fill="none" stroke={s.css.ink} strokeWidth="0.7" opacity="0.12" />
      <circle cx={CX} cy={CY} r="21" fill="none" stroke={s.css.glow} strokeWidth="1.6" opacity="0.45" />
      <circle cx={CX} cy={CY} r="12" fill="none" stroke={s.css.ink} strokeWidth="2.4" opacity="0.6" />
      <circle cx={CX} cy={CY} r="4.5" fill={s.css.ink} opacity="0.8" />
      <circle cx={CX} cy={CY} r="1.6" fill={s.css.paper} />
      <defs>
        <radialGradient id={`vg-${uid}`} cx="0.5" cy="0.5" r="0.6">
          <stop offset="0" stopColor={s.css.ink} stopOpacity="0.1" />
          <stop offset="1" stopColor={s.css.ink} stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width={W} height={H} fill={`url(#vg-${uid})`} />
      <circle cx="14" cy="20" r="1.8" fill={s.css.glow} opacity="0.6" />
    </g>
  ),

  spool: (s, uid) => {
    const reel = (cy: number) => (
      <g key={cy}>
        <circle cx={CX} cy={cy} r="15" fill="none" stroke={s.css.ink} strokeWidth="1.6" opacity="0.5" />
        <circle cx={CX} cy={cy} r="5" fill="none" stroke={s.css.ink} strokeWidth="1.4" opacity="0.6" />
        {starburstRays(6, CX, cy, 6, 15, s.css.ink)}
      </g>
    );
    return (
      <g>
        <rect x="0" y="0" width={W} height={H} fill={s.css.paper} />
        {reel(30)}
        {reel(90)}
        <path
          d={`M27 30 H${W - 27} M27 90 H${W - 27}`}
          fill="none"
          stroke={s.css.ink}
          strokeWidth="0.8"
          opacity="0.18"
        />
        <rect x="27" y="30" width="36" height="60" fill="none" stroke={s.css.ink} strokeWidth="0.7" opacity="0.12" />
        <line x1={CX - 20} y1={CY} x2={CX + 20} y2={CY} stroke={s.css.ink} strokeWidth="1.1" opacity="0.28" />
        <defs>
          <radialGradient id={`sp-${uid}`} cx="0.5" cy="0.5" r="0.55">
            <stop offset="0" stopColor={s.css.glow} stopOpacity="0.12" />
            <stop offset="1" stopColor={s.css.glow} stopOpacity="0" />
          </radialGradient>
        </defs>
        <rect width={W} height={H} fill={`url(#sp-${uid})`} />
        <circle cx={CX} cy={CY} r="4" fill={s.css.glow} opacity="0.5" />
      </g>
    );
  },
};

export function patternNames(): string[] {
  return Object.keys(PATTERNS);
}

/** Shared chrome around any pattern interior. */
export function CardBackArt({ sleeve }: { sleeve: Sleeve }) {
  const uid = `cb${Math.abs(hashCode(sleeve.id + sleeve.label))}`;
  const inner = (PATTERNS[sleeve.pattern] ?? PATTERNS.wavelength)(sleeve, uid);
  return (
    <svg
      className="card-back-art"
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      {inner}
      {/* unified chrome */}
      <defs>
        <radialGradient id={`vig-${uid}`} cx="0.5" cy="0.5" r="0.72">
          <stop offset="0.62" stopColor="#000" stopOpacity="0" />
          <stop offset="1" stopColor="#000" stopOpacity="0.5" />
        </radialGradient>
      </defs>
      <rect width={W} height={H} fill={`url(#vig-${uid})`} />
      <rect x="3.5" y="3.5" width={W - 7} height={H - 7} rx="7" fill="none" stroke={sleeve.css.ink} strokeWidth="2" />
      <rect x="7" y="7" width={W - 14} height={H - 14} rx="4" fill="none" stroke={sleeve.css.ink} strokeWidth="0.7" opacity="0.35" />
      {[[7.5, 7.5], [W - 7.5, 7.5], [7.5, H - 7.5], [W - 7.5, H - 7.5]].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="1.5" fill={sleeve.css.ink} opacity="0.7" />
      ))}
      <circle cx={CX} cy={CY} r="12.5" fill="none" stroke={sleeve.css.ink} strokeWidth="1" opacity="0.3" />
    </svg>
  );
}

/** stable, id-safe hash for defs ids */
function hashCode(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  return h;
}
