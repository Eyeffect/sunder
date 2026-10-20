import { fireEvent, render, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SleeveGallery } from "./CodexView";
import { CardBack } from "./CardBack";
import { importServerManifest } from "../test-manifest";
import type { SleeveDef } from "../sleeves";

const serverDefs: SleeveDef[] = importServerManifest().map((s) => ({
  id: s.id,
  label: s.label,
  palette: s.palette,
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
    const { container } = render(<SleeveGallery active="ember" />);
    const labelOf = (re: RegExp) =>
      [...container.querySelectorAll<HTMLElement>(".sleeve-tile-label")]
        .find((n) => re.test(n.textContent ?? ""));
    await waitFor(() => {
      for (const d of serverDefs) {
        expect(labelOf(new RegExp(`^${d.label}$`, "i"))).toBeTruthy();
      }
    });
    expect(labelOf(/^ember$/i)).toBeTruthy();
    const active = labelOf(/^ember$/i)!.parentElement as HTMLElement;
    expect(active.className).toContain("active");
  });

  it("applies the picked sleeve via the onPick callback", async () => {
    vi.stubGlobal("fetch", vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve({ sleeves: serverDefs }) }),
    ));
    const onPick = vi.fn();
    const { container } = render(<SleeveGallery active="ember" onPick={onPick} />);
    const target = await waitFor(() => {
      const el = [...container.querySelectorAll<HTMLElement>(".sleeve-tile-label")]
        .find((n) => /^spool$/i.test(n.textContent ?? ""));
      if (!el) throw new Error("spool label not rendered yet");
      return el;
    });
    fireEvent.click(target.parentElement as HTMLElement);
    expect(onPick).toHaveBeenCalledWith("spool");
  });
});

describe("CardBack gallery rendering", () => {
  it("renders hydrated manifest sleeves with their art", () => {
    for (const s of importServerManifest()) {
      const { container, unmount } = render(<CardBack sleeve={s.id} />);
      expect(
        container.querySelector(`.card-back--${s.id}`),
      ).toBeTruthy();
      unmount();
    }
  });
});
