export const PLANES: Record<string, { label: string; color: string }> = {
  neon_frequency: { label: "Neon Frequency", color: "#ffb545" },
  cinderworks: { label: "Cinderworks", color: "#ff5a3c" },
  driftglass: { label: "Driftglass", color: "#5ff2e0" },
  sporewake: { label: "Sporewake", color: "#9dff5f" },
};

export function planeMeta(plane: string | undefined): { label: string; color: string } {
  if (plane && PLANES[plane]) return PLANES[plane];
  return { label: plane || "radio", color: "#ffb545" };
}
