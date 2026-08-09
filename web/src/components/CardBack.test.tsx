import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
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
    expect(container.querySelector(".card-back--mandala")).toBeTruthy();
  });
});
