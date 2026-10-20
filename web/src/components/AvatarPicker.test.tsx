import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AvatarPicker } from "./AvatarPicker";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("AvatarPicker", () => {
  it("loads the server avatars and picks one", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          json: () =>
            Promise.resolve({
              avatars: [{ id: "custom", label: "Custom", glyph: "✳" }],
            }),
        }),
      ),
    );
    const onPick = vi.fn();
    render(
      <AvatarPicker current="custom" ink="var(--cyan)" onPick={onPick} onClose={() => {}} />,
    );
    const option = await screen.findByRole("button", { name: /Custom/ });
    expect(option).toHaveClass("active");
    fireEvent.click(option);
    expect(onPick).toHaveBeenCalledWith("custom");
  });

  it("closes on Escape and on backdrop click", () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    const onClose = vi.fn();
    const { container } = render(
      <AvatarPicker current="frequency" ink="var(--amber)" onPick={() => {}} onClose={onClose} />,
    );
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
    fireEvent.click(container.querySelector(".overlay")!);
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it("keeps the fallback list when the endpoint fails", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    render(
      <AvatarPicker current="frequency" ink="var(--amber)" onPick={() => {}} onClose={() => {}} />,
    );
    await waitFor(() => expect(screen.getByRole("button", { name: /Call Sign/ })).toBeTruthy());
  });
});
