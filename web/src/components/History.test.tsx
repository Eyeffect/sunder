import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { History } from "./History";
import type { HistoryEvent } from "../types";

const events: HistoryEvent[] = [
  {
    kind: "play",
    text: "Station 1 plays Neon Drifter.",
    station: 0,
    card: {
      serial: 1,
      name: "Neon Drifter",
      type: "BROADCAST",
      plane: "neon_frequency",
      cost: 3,
      keywords: ["LOUD"],
      is_token: false,
      station: 0,
    },
  },
  {
    kind: "damage",
    text: "Cinder Hound takes 2 Noise.",
    station: 1,
    card: {
      serial: 2,
      name: "Cinder Hound",
      type: "BROADCAST",
      plane: "cinderworks",
      cost: 2,
      keywords: [],
      is_token: false,
      station: 1,
    },
  },
  {
    kind: "reveal",
    text: "Station 0 reveals a B-SIDE: Ghost Tune.",
    station: 0,
  },
];

describe("History", () => {
  it("renders newest event first", () => {
    const { container } = render(<History history={events} />);
    const badges = container.querySelectorAll(".history-badge");
    expect(badges.length).toBe(3);
    expect(badges[0].getAttribute("aria-label")).toBe(
      "Station 0 reveals a B-SIDE: Ghost Tune.",
    );
    expect(badges[2].getAttribute("aria-label")).toBe(
      "Station 1 plays Neon Drifter.",
    );
  });

  it("shows a mini card for play events", () => {
    render(<History history={events} />);
    expect(screen.getByText("3")).toBeInTheDocument();
    const mini = document.querySelector(".mini-card");
    expect(mini).not.toBeNull();
  });

  it("shows a tooltip on hover", () => {
    render(<History history={events} />);
    const badge = screen.getByLabelText("Station 1 plays Neon Drifter.");
    fireEvent.mouseEnter(badge);
    expect(screen.getByText(/plays Neon Drifter/)).toBeInTheDocument();
    fireEvent.mouseLeave(badge);
    expect(screen.queryByText(/plays Neon Drifter/)).not.toBeInTheDocument();
  });

  it("caps the column to the newest 10 icons", () => {
    const many: HistoryEvent[] = Array.from({ length: 15 }, (_, i) => ({
      kind: "system",
      text: `event ${i}`,
      station: 0,
    }));
    const { container } = render(<History history={many} />);
    const badges = container.querySelectorAll(".history-badge");
    expect(badges.length).toBe(10);
    expect(badges[0].getAttribute("aria-label")).toBe("event 14");
  });

  it("drops turn entries even if the server sends them", () => {
    const withTurn = [
      { kind: "turn" as never, text: "--- Turn 1 — Station 1 ---", station: 0 },
      ...events,
    ];
    const { container } = render(<History history={withTurn as unknown as HistoryEvent[]} />);
    const badges = container.querySelectorAll(".history-badge");
    expect(badges.length).toBe(3);
    expect(
      container.querySelector('[aria-label="--- Turn 1 — Station 1 ---"]'),
    ).toBeNull();
  });

  it("masks a secret B-SIDE play", () => {
    const secret: HistoryEvent[] = [
      {
        kind: "play",
        text: "Station 2 plays a secret B-SIDE.",
        station: 1,
        card: {
          serial: 9,
          name: "???",
          type: null,
          plane: "",
          cost: null,
          keywords: ["B_SIDE"],
          is_token: false,
          station: 1,
        },
      },
    ];
    render(<History history={secret} />);
    const badge = screen.getByLabelText("Station 2 plays a secret B-SIDE.");
    fireEvent.mouseEnter(badge);
    expect(screen.getByText(/plays a secret B-SIDE/)).toBeInTheDocument();
    expect(screen.getByText("???")).toBeInTheDocument();
    expect(screen.queryAllByText("?").length).toBeGreaterThan(0);
  });
});
