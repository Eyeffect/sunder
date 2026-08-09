export interface Sleeve {
  id: string;
  label: string;
  colors: { primary: string; glow: string };
  pattern: string;
  emblem?: string;
  asset?: string;
}

export const SLEEVES: Record<string, Sleeve> = {
  ember: {
    id: "ember",
    label: "Ember",
    colors: { primary: "var(--amber)", glow: "var(--amber)" },
    pattern: "mandala",
    emblem: "◉",
  },
  static: {
    id: "static",
    label: "Static",
    colors: { primary: "var(--magenta)", glow: "var(--magenta)" },
    pattern: "mandala",
    emblem: "◉",
  },
  default: {
    id: "default",
    label: "Default",
    colors: { primary: "var(--amber)", glow: "var(--amber)" },
    pattern: "mandala",
    emblem: "◉",
  },
};

export function sleeveOf(id: string): Sleeve {
  return SLEEVES[id] ?? SLEEVES.default;
}
