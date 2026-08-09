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
uniform float uTurnT;

out vec4 fragColor;

vec2 hash(vec2 p) {
    return fract(sin(mod(p.xy * 2.94 - p.yx * 2.77, 99. + p.x)) * 691.5);
}

void mainImage(out vec4 Color, in vec2 Coord) {
    float pixelSize = 3.0;
    vec2 pixCoord = floor(Coord / pixelSize) * pixelSize + (pixelSize * 0.5);

    vec2 center = iResolution.xy * 0.5;
    vec2 toCenter = pixCoord - center;
    float dist = length(toCenter) / iResolution.y;

    float pulseSpeed = 0.1;
    float swirlPulse = sin(iTime * pulseSpeed);

    float swirlStrength = 5.0;
    float angle = pow(dist, 2.0) * swirlStrength * swirlPulse;

    float cosA = cos(angle);
    float sinA = sin(angle);
    mat2 rotationMat = mat2(cosA, -sinA, sinA, cosA);

    vec2 swirledCoord = center + rotationMat * toCenter;

    vec2 u = swirledCoord / iResolution.xy + hash(swirledCoord) * .02;
    float s = hash(floor(u * mat2(9, -3, 7, -4))).x;
    float l = length(swirledCoord - center) / iResolution.y;

    vec3 b = .5 + .5 * cos(l * vec3(40. - l * l, 40.5, 41.) - iTime + s * 4.) / (.2 + l * 3.);

    vec3 baseColor = 0.5 + 0.5 * cos(iTime * 0.5 + vec3(0.0, 2.0, 4.0));
    vec3 glowColor = 0.7 + 0.3 * sin(iTime * 0.3 + vec3(1.5, 3.0, 0.0));

    vec3 g = mix(hash(floor(swirledCoord / 2.)).xxx * baseColor, glowColor, pow(s, 5.) * .2);

    Color = vec4(pow(g, .5 + b * b * 80.) / (.5 + l), 1.);
}

void main() {
    mainImage(fragColor, vec2(gl_FragCoord.x, iResolution.y - gl_FragCoord.y));
}
`;

interface BackgroundShaderProps {
  turnSide?: boolean | null;
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

    const reduced =
      (typeof window.matchMedia === "function" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches) ||
      false;

    let hidden = document.hidden;
    let stopped = false;

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
      gl.uniform1f(timeLoc, performance.now() / 1000);
      const ts = turnRef.current;
      gl.uniform1f(turnLoc, ts === null ? 0.5 : ts ? 1 : 0);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      if (!reduced) rafRef.current = requestAnimationFrame(frame);
    };

    if (reduced) {
      gl.uniform1f(timeLoc, 0);
      gl.uniform1f(turnLoc, turnRef.current === true ? 1 : 0);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    } else {
      rafRef.current = requestAnimationFrame(frame);
    }

    const onVisibility = () => {
      hidden = document.hidden;
      if (!hidden && !reduced && rafRef.current === null) {
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
