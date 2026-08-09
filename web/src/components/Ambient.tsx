import type { CSSProperties } from "react";

const AMBIENT_GLOWS = [
  { top: "8%", left: "12%", size: 460, color: "rgba(255,181,69,0.22)", dx: "90px", dy: "-30px", dur: 28 },
  { top: "52%", left: "74%", size: 500, color: "rgba(95,242,224,0.17)", dx: "-80px", dy: "60px", dur: 34 },
  { top: "74%", left: "26%", size: 380, color: "rgba(255,62,168,0.15)", dx: "70px", dy: "50px", dur: 26 },
  { top: "16%", left: "84%", size: 320, color: "rgba(157,255,95,0.12)", dx: "-50px", dy: "40px", dur: 38 },
  { top: "84%", left: "58%", size: 360, color: "rgba(255,181,69,0.13)", dx: "-60px", dy: "-40px", dur: 31 },
  { top: "38%", left: "2%", size: 280, color: "rgba(95,242,224,0.10)", dx: "50px", dy: "30px", dur: 42 },
];

const DRIFT_SHAPES = [
  { left: "4%", size: 30, dur: 20, delay: -2, color: "var(--amber)", fill: "rgba(255,181,69,0.05)" },
  { left: "11%", size: 18, dur: 17, delay: -9, color: "var(--cyan)", fill: "rgba(95,242,224,0.04)" },
  { left: "19%", size: 46, dur: 28, delay: -14, color: "var(--magenta)", fill: "rgba(255,62,168,0.04)" },
  { left: "28%", size: 26, dur: 19, delay: -5, color: "var(--amber)", fill: "rgba(255,181,69,0.05)" },
  { left: "38%", size: 16, dur: 15, delay: -11, color: "var(--cyan)", fill: "rgba(95,242,224,0.03)" },
  { left: "47%", size: 38, dur: 24, delay: -3, color: "var(--amber)", fill: "rgba(255,181,69,0.05)" },
  { left: "55%", size: 22, dur: 18, delay: -16, color: "var(--magenta)", fill: "rgba(255,62,168,0.04)" },
  { left: "64%", size: 42, dur: 27, delay: -7, color: "var(--cyan)", fill: "rgba(95,242,224,0.04)" },
  { left: "73%", size: 20, dur: 22, delay: -12, color: "var(--amber)", fill: "rgba(255,181,69,0.04)" },
  { left: "82%", size: 34, dur: 21, delay: -6, color: "var(--magenta)", fill: "rgba(255,62,168,0.04)" },
  { left: "91%", size: 14, dur: 16, delay: -18, color: "var(--cyan)", fill: "rgba(95,242,224,0.03)" },
];

const CARD_FLOATS = [
  { left: "7%", top: "62%", size: 52, rotA: 12, rotB: 17, color: "rgba(255,181,69,0.22)", fill: "rgba(255,181,69,0.04)", dur: 14, delay: -3 },
  { left: "18%", top: "28%", size: 44, rotA: -22, rotB: -16, color: "rgba(95,242,224,0.18)", fill: "rgba(95,242,224,0.03)", dur: 18, delay: -9 },
  { left: "32%", top: "72%", size: 60, rotA: 6, rotB: 11, color: "rgba(255,62,168,0.14)", fill: "rgba(255,62,168,0.03)", dur: 16, delay: -12 },
  { left: "52%", top: "18%", size: 48, rotA: -8, rotB: -3, color: "rgba(255,181,69,0.17)", fill: "rgba(255,181,69,0.03)", dur: 20, delay: -5 },
  { left: "68%", top: "66%", size: 36, rotA: 18, rotB: 23, color: "rgba(95,242,224,0.20)", fill: "rgba(95,242,224,0.04)", dur: 15, delay: -7 },
  { left: "80%", top: "34%", size: 56, rotA: -14, rotB: -9, color: "rgba(157,255,95,0.13)", fill: "rgba(157,255,95,0.03)", dur: 22, delay: -15 },
  { left: "91%", top: "54%", size: 40, rotA: 4, rotB: 9, color: "rgba(255,181,69,0.15)", fill: "rgba(255,181,69,0.03)", dur: 17, delay: -2 },
];

export function AmbientBackground() {
  return (
    <div className="ambient-bg" aria-hidden="true">
      <div className="ambient-spotlight" />
      {AMBIENT_GLOWS.map((g, i) => (
        <div
          key={`g${i}`}
          className="ambient-glow"
          style={
            {
              top: g.top,
              left: g.left,
              width: g.size,
              height: g.size,
              background: g.color,
              "--dx": g.dx,
              "--dy": g.dy,
              animationDuration: `${g.dur}s`,
            } as CSSProperties
          }
        />
      ))}
      {DRIFT_SHAPES.map((s, i) => (
        <div
          key={`s${i}`}
          className="drift-shape"
          style={
            {
              left: s.left,
              width: s.size,
              height: s.size,
              "--shape-color": s.color,
              "--shape-fill": s.fill,
              animationDuration: `${s.dur}s`,
              animationDelay: `${s.delay}s`,
            } as CSSProperties
          }
        />
      ))}
      {CARD_FLOATS.map((f, i) => (
        <div
          key={`f${i}`}
          className="card-float"
          style={
            {
              left: f.left,
              top: f.top,
              width: f.size,
              "--fc": f.color,
              "--ff": f.fill,
              "--ra": `${f.rotA}deg`,
              "--rb": `${f.rotB}deg`,
              animationDuration: `${f.dur}s`,
              animationDelay: `${f.delay}s`,
            } as CSSProperties
          }
        />
      ))}
    </div>
  );
}

export function CrtOverlay() {
  return (
    <div className="crt-overlay" aria-hidden="true">
      <div className="crt-scanlines" />
      <div className="crt-vignette" />
    </div>
  );
}
