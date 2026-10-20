import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import manifest from "../../../sunder/cards/avatars.json";
import { AvatarGlyph } from "./AvatarGlyph";

describe("AvatarGlyph", () => {
  it("draws an SVG for every manifest icon", () => {
    for (const avatar of manifest.avatars) {
      const { container, unmount } = render(
        <AvatarGlyph id={avatar.id} glyph={avatar.glyph} />,
      );
      const svg = container.querySelector("svg");
      expect(svg, `${avatar.id} has no SVG geometry`).toBeTruthy();
      expect(svg?.querySelectorAll("path, circle, rect").length).toBeGreaterThan(0);
      unmount();
    }
  });

  it("falls back to the manifest glyph for unknown ids", () => {
    const { container } = render(<AvatarGlyph id="custom" glyph="✳" />);
    expect(container.querySelector("svg")).toBeNull();
    expect(container.textContent).toBe("✳");
  });
});
