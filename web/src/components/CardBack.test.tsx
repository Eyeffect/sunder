import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { artIds } from "../backPatterns";
import { CardBack } from "./CardBack";

describe("CardBack", () => {
  it("renders the sleeve emblem for a known sleeve", () => {
    render(<CardBack sleeve="ember" />);
    expect(screen.getByText("◉")).toBeTruthy();
  });

  it("renders a secret marker when secret", () => {
    render(<CardBack sleeve="static" secret />);
    expect(screen.getByText("?")).toBeTruthy();
  });

  it("falls back to the default sleeve for unknown ids", () => {
    const { container } = render(<CardBack sleeve="nope" />);
    expect(container.querySelector(".card-back--default")).toBeTruthy();
  });

  it("defines every palette variable the rendered art references", () => {
    for (const id of artIds()) {
      const { container, unmount } = render(<CardBack sleeve={id} />);
      const root = container.querySelector(".card-back") as HTMLElement;
      const art = container.querySelector(".card-back-art") as Element;
      const referenced = new Set(
        [...art.outerHTML.matchAll(/var\((--sleeve-[\w-]+)\)/g)].map((m) => m[1]),
      );
      expect(referenced.size, `${id} references no palette vars`).toBeGreaterThan(0);
      for (const name of referenced) {
        expect(root.style.getPropertyValue(name), `${id} does not define ${name}`).toBeTruthy();
      }
      unmount();
    }
  });
});
