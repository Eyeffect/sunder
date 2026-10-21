import "@testing-library/jest-dom/vitest";

import { vi } from "vitest";

// jsdom doesn't implement canvas; return null like an unsupported context would.
Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
  configurable: true,
  value: vi.fn(() => null),
});
