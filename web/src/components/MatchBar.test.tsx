import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { MatchMeta } from "../types";
import { MatchBar } from "./MatchBar";

const meta = (o: Partial<MatchMeta> = {}): MatchMeta => ({
  mode: "pvp",
  code: "ABC234",
  seat: 0,
  opponent_connected: true,
  turn_seconds: 75,
  turn_remaining: 40,
  ...o,
});

describe("MatchBar", () => {
  it("shows the room, rival status and the turn clock", () => {
    render(
      <MatchBar match={meta()} deadline={Date.now() + 40_000} myTurn gameOver={false}
        onConcede={() => {}} />,
    );
    expect(screen.getByText("ROOM ABC234")).toBeInTheDocument();
    expect(screen.getByText("RIVAL ON AIR")).toBeInTheDocument();
    expect(screen.getByText(/YOUR TURN 40s/)).toBeInTheDocument();
  });

  it("flags a dropped rival", () => {
    render(
      <MatchBar match={meta({ opponent_connected: false })} deadline={null} myTurn={false}
        gameOver={false} onConcede={() => {}} />,
    );
    expect(screen.getByText(/RIVAL SIGNAL LOST/)).toBeInTheDocument();
    expect(screen.queryByText(/\ds$/)).not.toBeInTheDocument();
  });

  it("asks for confirmation before conceding", () => {
    const onConcede = vi.fn();
    render(
      <MatchBar match={meta()} deadline={null} myTurn gameOver={false} onConcede={onConcede} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "CONCEDE" }));
    expect(onConcede).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "KEEP PLAYING" }));
    fireEvent.click(screen.getByRole("button", { name: "CONCEDE" }));
    fireEvent.click(screen.getByRole("button", { name: "YES, CONCEDE" }));
    expect(onConcede).toHaveBeenCalledTimes(1);
  });

  it("hides concede and clock once the game is over", () => {
    render(
      <MatchBar match={meta()} deadline={Date.now() + 5000} myTurn gameOver
        onConcede={() => {}} />,
    );
    expect(screen.queryByRole("button", { name: "CONCEDE" })).not.toBeInTheDocument();
    expect(screen.queryByText(/YOUR TURN/)).not.toBeInTheDocument();
  });
});
