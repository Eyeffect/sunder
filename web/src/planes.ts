export interface PlaneMeta {
  label: string;
  color: string;
  /** two-letter station ID, painted as a watermark on card faces */
  code: string;
}

export const PLANES: Record<string, PlaneMeta> = {
  neon_frequency: { label: "Neon Frequency", color: "#ffb545", code: "NF" },
  cinderworks: { label: "Cinderworks", color: "#ff5a3c", code: "CW" },
  driftglass: { label: "Driftglass", color: "#5ff2e0", code: "DG" },
  sporewake: { label: "Sporewake", color: "#9dff5f", code: "SW" },
};

export function planeMeta(plane: string | undefined): PlaneMeta {
  if (plane && PLANES[plane]) return PLANES[plane];
  return { label: plane || "radio", color: "#ffb545", code: "FM" };
}
