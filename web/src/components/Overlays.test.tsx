import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Inspector } from "./Overlays";

describe("Inspector", () => {
  it("masks a rival's hidden B-SIDE", () => {
    render(
      <Inspector
        card={{
          name: "???",
          hidden: true,
          keywords: ["B_SIDE"],
        }}
      />,
    );
    expect(screen.getByText("??? (hidden B-SIDE)")).toBeInTheDocument();
    expect(screen.getByText("B_SIDE")).toBeInTheDocument();
    expect(screen.queryByText(/rules/)).not.toBeInTheDocument();
  });

  it("reveals your own secret on hover", () => {
    render(
      <Inspector
        card={{
          name: "Deep Secret",
          hidden: true,
          keywords: ["B_SIDE", "LOUD"],
          rules: "Deal 1 Noise when a Broadcast airs.",
          flavor: "Stay tuned.",
        }}
      />,
    );
    expect(screen.getByText("Deep Secret")).toBeInTheDocument();
    expect(screen.getByText("B_SIDE LOUD")).toBeInTheDocument();
    expect(
      screen.getByText(/Deal 1 Noise when a Broadcast airs/),
    ).toBeInTheDocument();
  });
});
