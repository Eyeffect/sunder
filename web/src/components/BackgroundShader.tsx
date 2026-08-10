import { useEffect, useRef } from "react";

const VERTEX_SRC = `#version 300 es
void main() {
  vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
`;

const FRAGMENT_SRC = `#version 300 es
precision highp float;

uniform vec2 iResolution;
uniform float iTime;
uniform float uTurnT;      // eased 0..1, 0 = rival's turn, 1 = your turn, 0.5 = neutral
uniform float uSpinAngle;  // accumulated rotation angle in radians, integrated in JS

out vec4 fragColor;

// ============================================================
// Hash function — generates pseudo-random 2D noise from a 2D input.
// Used for grain/dithering and cell-based randomness.
// ============================================================
vec2 hash(vec2 p) {
    return fract(sin(mod(p.xy * 2.94 - p.yx * 2.77, 99.0 + p.x)) * 691.5);
}

void mainImage(out vec4 Color, in vec2 Coord) {

    // ------------------------------------------------------------
    // 1. PIXELATION
    // Snap the screen coordinate to a coarse grid to get a
    // chunky/retro pixel look instead of smooth per-pixel detail.
    // ------------------------------------------------------------
    float pixelSize = 3.0;
    vec2 pixelatedCoord = floor(Coord / pixelSize) * pixelSize + (pixelSize * 0.5);


    // ------------------------------------------------------------
    // 2. DISTANCE FROM CENTER
    // ------------------------------------------------------------
    float centerOffsetX = 9.5;   // increase to move right, decrease to move left
    float centerOffsetY = -85.1; // increase to move up, decrease to move down
    vec2 center = iResolution.xy * 0.5 + vec2(0.1 + centerOffsetX, 0.1 + centerOffsetY);
    vec2 offsetFromCenter = pixelatedCoord - center;
    float normalizedDist = length(offsetFromCenter) / iResolution.y;


    // ------------------------------------------------------------
    // 3. SWIRL / ROTATION
    // Two combined effects:
    //   a) The existing distance-based pulse/twist (unchanged look).
    //   b) A continuous spin driven by uSpinAngle, which JS accumulates
    //      frame-by-frame using delta time (NOT derived from iTime
    //      directly) — this keeps spin speed constant regardless of
    //      how long the session has been running.
    // ------------------------------------------------------------
    float swirlPulseSpeed = 0.1;
    float swirlPulse = sin(iTime * swirlPulseSpeed);   // oscillates -1..1
    float swirlStrength = 3.0;
    float pulseAngle = pow(normalizedDist, 2.0) * swirlStrength * swirlPulse;

    float swirlAngle = pulseAngle + uSpinAngle;

    float cosA = cos(swirlAngle);
    float sinA = sin(swirlAngle);
    mat2 rotation = mat2(cosA, -sinA, sinA, cosA);
    vec2 swirledCoord = center + rotation * offsetFromCenter;


    // ------------------------------------------------------------
    // 4. NOISE / GRAIN
    // Small random jitter + a cell-based random value (grain), used to
    // break up flat color and add sparkle/texture.
    // ------------------------------------------------------------
    vec2 uv = swirledCoord / iResolution.xy + hash(swirledCoord) * 0.02;
    float grain = hash(floor(uv * mat2(9, -3, 7, -4))).x;
    float swirledDist = length(swirledCoord - center) / iResolution.y;


    // ------------------------------------------------------------
    // 5. RING / RIPPLE PATTERN
    // Concentric cosine rings based on distance from center,
    // animated over time. Feeds into the brightness exponent below.
    // ------------------------------------------------------------
    vec3 ringPattern =
        0.4 + 0.5 * cos(
            swirledDist * vec3(40.0 - swirledDist * swirledDist, 40.5, 41.0)
            - iTime
            + grain * 4.0
        ) / (0.2 + swirledDist * 3.0);


    // ------------------------------------------------------------
    // 6. COLOR — Amber on your turn, Magenta (rival) on theirs.
    // uTurnT is eased smoothly in JS each frame, so the color blend
    // transitions gradually rather than snapping.
    // ------------------------------------------------------------
    vec3 amber   = vec3(1.0, 0.75, 0.0);   // your turn
    vec3 magenta = vec3(1.0, 0.24, 0.66);  // rival's turn (--magenta #ff3ea8)
    float colorShift = 1.0 - uTurnT;       // 0 = your turn (amber), 1 = rival (magenta)

    vec3 baseColor = mix(amber, magenta, colorShift);
    vec3 glowColor = mix(magenta, amber, colorShift) * 1.1; // offset phase, slightly brighter


    // ------------------------------------------------------------
    // 7. COMBINE COLOR + GRAIN + GLOW
    // ------------------------------------------------------------
    vec3 grainColor = hash(floor(swirledCoord / 2.0)).xxx * baseColor;
    float glowWeight = pow(grain, 5.0) * 0.2;
    vec3 finalColor = mix(grainColor, glowColor, glowWeight);


    // ------------------------------------------------------------
    // 8. FINAL OUTPUT
    // Ring pattern controls contrast via the exponent; overall
    // brightness fades out with distance from center.
    // ------------------------------------------------------------
    vec3 shaded = pow(finalColor, 0.5 + ringPattern * ringPattern * 80.0);
    Color = vec4(shaded / (0.5 + swirledDist), 1.0);
}

void main() {
    mainImage(fragColor, vec2(gl_FragCoord.x, iResolution.y - gl_FragCoord.y));
}
`;

interface BackgroundShaderProps {
  turnSide?: boolean | null; // true = your turn, false = rival's turn, null = neutral
}

export function BackgroundShader({ turnSide = null }: BackgroundShaderProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rafRef = useRef<number | null>(null);
  const turnRef = useRef<boolean | null>(turnSide);

  useEffect(() => {
    turnRef.current = turnSide;
  }, [turnSide]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    let gl: WebGL2RenderingContext | null = null;
    try {
      gl = canvas.getContext("webgl2");
    } catch {
      gl = null;
    }
    if (!gl) return;

    const compile = (type: number, src: string): WebGLShader | null => {
      const sh = gl.createShader(type);
      if (!sh) return null;
      gl.shaderSource(sh, src);
      gl.compileShader(sh);
      if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
        console.error("sunder bg shader compile error:", gl.getShaderInfoLog(sh));
        gl.deleteShader(sh);
        return null;
      }
      return sh;
    };

    const vs = compile(gl.VERTEX_SHADER, VERTEX_SRC);
    const fs = compile(gl.FRAGMENT_SHADER, FRAGMENT_SRC);
    if (!vs || !fs) return;

    const prog = gl.createProgram();
    if (!prog) return;
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      console.error("sunder bg program link error:", gl.getProgramInfoLog(prog));
      return;
    }
    gl.useProgram(prog);

    const resLoc = gl.getUniformLocation(prog, "iResolution");
    const timeLoc = gl.getUniformLocation(prog, "iTime");
    const turnLoc = gl.getUniformLocation(prog, "uTurnT");
    const spinAngleLoc = gl.getUniformLocation(prog, "uSpinAngle");

    const reduced =
      (typeof window.matchMedia === "function" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches) ||
      false;

    let hidden = document.hidden;
    let stopped = false;

    let turnVal = 0.5;
    let spinAngle = 0;
    let lastFrameTime = performance.now();
    const spinSpeed = 0.15; // radians/sec at full commitment (spinDirection = ±1); lower = slower spin

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = Math.max(1, Math.round(window.innerWidth * dpr));
      const h = Math.max(1, Math.round(window.innerHeight * dpr));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
      gl.viewport(0, 0, w, h);
      gl.uniform2f(resLoc, w, h);
    };
    resize();

    const frame = () => {
      if (stopped || hidden) return;

      const now = performance.now();
      const dt = Math.min((now - lastFrameTime) / 1000, 0.1); // clamp guards against huge jumps after tab-switch
      lastFrameTime = now;

      gl.uniform1f(timeLoc, now / 1000);

      const ts = turnRef.current;
      const target = ts === null ? 0.5 : ts ? 1 : 0;
      turnVal += (target - turnVal) * 0.025;
      gl.uniform1f(turnLoc, turnVal);

      // Integrate spin angle each frame using delta time — NOT iTime directly —
      // so angular speed stays constant no matter how long the session runs.
      const spinDirection = turnVal * 2.0 - 1.0; // -1 (rival) .. 0 (neutral) .. 1 (your turn)
      spinAngle += spinSpeed * spinDirection * dt;
      gl.uniform1f(spinAngleLoc, spinAngle);

      gl.drawArrays(gl.TRIANGLES, 0, 3);
      if (!reduced) rafRef.current = requestAnimationFrame(frame);
    };

    if (reduced) {
      gl.uniform1f(timeLoc, 0);
      gl.uniform1f(turnLoc, turnRef.current === true ? 1 : 0);
      gl.uniform1f(spinAngleLoc, 0);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    } else {
      lastFrameTime = performance.now();
      rafRef.current = requestAnimationFrame(frame);
    }

    const onVisibility = () => {
      hidden = document.hidden;
      if (!hidden && !reduced && rafRef.current === null) {
        lastFrameTime = performance.now(); // avoid a big dt jump after returning to tab
        rafRef.current = requestAnimationFrame(frame);
      }
    };
    const onResize = () => resize();

    window.addEventListener("resize", onResize);
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      stopped = true;
      window.removeEventListener("resize", onResize);
      document.removeEventListener("visibilitychange", onVisibility);
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, []);

  return (
    <div className="shader-bg" aria-hidden="true">
      <canvas ref={canvasRef} />
    </div>
  );
}
