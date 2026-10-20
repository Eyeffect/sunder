import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PlayerState } from "../types";
import { PlayerZone } from "./PlayerZone";

const player: PlayerState = {
  index: 0,
  sleeve: "ember",
  sleeve_ink: "cyan",
  avatar: "cinder",
  avatar_glyph: "⌁",
  signal: 20,
  max_signal: 30,
  bandwidth: 1,
  max_bandwidth: 1,
  hand_count: 3,
  static_count: 1,
  playlist_count: 2,
  board: [],
};

describe("PlayerZone avatar", () => {
  it("tints the profile glyph with sleeve ink and opens the picker", () => {
    const onClick = vi.fn();
    const { getByRole } = render(
      <PlayerZone title="YOUR STATION" player={player} mine onAvatarClick={onClick} />,
    );
    const btn = getByRole("button", { name: "Choose profile icon" });
    expect(btn).toHaveTextContent("⌁");
    expect(btn).toHaveStyle({ color: "var(--cyan)" });
    fireEvent.click(btn);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("falls back to the default glyph and is inert for the rival", () => {
    const { container, queryByRole } = render(
      <PlayerZone
        title="RIVAL STATION"
        player={{ ...player, index: 1, avatar: undefined, avatar_glyph: undefined }}
      />,
    );
    expect(queryByRole("button", { name: "Choose profile icon" })).toBeNull();
    const frame = container.querySelector(".avatar-frame.opp");
    expect(frame).toHaveTextContent("◉");
    expect(frame).toHaveAttribute("aria-hidden", "true");
  });
});
