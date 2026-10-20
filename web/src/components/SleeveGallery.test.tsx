import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SleeveGallery } from "./CodexView";
import { CardBack } from "./CardBack";
import { importServerManifest } from "../test-manifest";
import type { SleeveDef } from "../sleeves";
import { sleeveOf } from "../sleeves";

const serverDefs: SleeveDef[] = importServerManifest().map((s) => ({
  id: s.id,
  label: s.label,
  pattern: s.pattern,
  palette: s.palette,
  emblem: s.emblem,
}));

describe("SleeveGallery", () => {
  it("renders every sleeve the server manifest defines", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        expect(String(url)).toContain("/api/sleeves");
        return Promise.resolve({
          json: () => Promise.resolve({ sleeves: serverDefs }),
        });
      }),
    );
    render(<SleeveGallery active="ember" />);
    await waitFor(() => {
      for (const d of serverDefs) {
        expect(screen.getByText(new RegExp(`^${d.label}$`, "i"))).toBeInTheDocument();
      }
    });
    expect(screen.getByText(/^ember$/i))
      .toHaveClass("sleeve-tile-label");
    const active = screen.getByText(/^ember$/i).parentElement as HTMLElement;
    expect(active.className).toContain("active");
  });

  it("applies the picked sleeve via the onPick callback", async () => {
    vi.stubGlobal("fetch", vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve({ sleeves: serverDefs }) }),
    ));
    const onPick = vi.fn();
    render(<SleeveGallery active="ember" onPick={onPick} />);
    const target = await screen.findByText(/^spool$/i);
    fireEvent.click(target.parentElement as HTMLElement);
    expect(onPick).toHaveBeenCalledWith("spool");
  });
});

describe("CardBack gallery rendering", () => {
  it("renders hydrated manifest sleeves with their emblems", () => {
    for (const s of importServerManifest()) {
      const { container, unmount } = render(<CardBack sleeve={s.id} />);
      expect(
        container.querySelector(`.card-back--${sleeveOf(s.id).pattern}`),
      ).toBeTruthy();
      unmount();
    }
  });
});
