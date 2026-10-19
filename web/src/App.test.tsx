import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type {
  BoardCard,
  HandCard,
  PlayerState,
  Snapshot,
} from "./types";

const ws = vi.hoisted(() => {
  const sendMock = vi.fn();
  class GameSocket {
    static last: GameSocket | null = null;
    onState: (s: Snapshot) => void = () => {};
    onError: (m: string) => void = () => {};
    onOpen: () => void = () => {};
    send = sendMock;
    connect() {}
    close() {}
    constructor() {
      GameSocket.last = this;
    }
  }
  return { sendMock, GameSocket };
});

vi.mock("./ws", () => ({ GameSocket: ws.GameSocket }));

vi.stubGlobal(
  "fetch",
  vi.fn((url: string) => {
    const data = String(url).includes("/api/keywords") ? { keywords: [] } : { cards: [] };
    return Promise.resolve({ json: () => Promise.resolve(data) });
  }),
);

function player(overrides: Partial<PlayerState> = {}): PlayerState {
  return {
    index: 0,
    sleeve: "ember",
    signal: 20,
    max_signal: 30,
    bandwidth: 1,
    max_bandwidth: 1,
    hand_count: 0,
    static_count: 0,
    playlist_count: 0,
    board: [],
    ...overrides,
  };
}

function snapshot(overrides: Partial<Snapshot> = {}): Snapshot {
  return {
    turn: 1,
    current: 0,
    phase: "MAIN",
    winner: null,
    status: "Turn 1 | Station 1 | Signal 20/30 vs 20/30",
    viewer: 0,
    can_act: true,
    players: {},
    me: player({ index: 0 }),
    foe: player({ index: 1 }),
    hand: [],
    log: [],
    log_offset: 0,
    history: [],
    ...overrides,
  };
}

function handCard(overrides: Partial<HandCard> = {}): HandCard {
  return {
    serial: 10,
    id: "card_10",
    name: "Neon Drifter",
    cost: 3,
    type: "BROADCAST",
    keywords: ["RUSH"],
    atk: 3,
    def: 2,
    rules: "RUSH — attacks the turn it airs.",
    flavor: "",
    is_playable: true,
    needs_target: false,
    legal_targets: [],
    ...overrides,
  };
}

function boardCard(overrides: Partial<BoardCard> = {}): BoardCard {
  return {
    serial: 1,
    hidden: false,
    type: "BROADCAST",
    name: "Vinyl Golem",
    keywords: [],
    is_token: false,
    cost: 4,
    atk: 3,
    def: 5,
    damage: 0,
    can_attack: false,
    attack_targets: [],
    ...overrides,
  };
}

function pump(snap: Snapshot): void {
  const sock = ws.GameSocket.last;
  act(() => sock?.onState(snap));
}

beforeEach(() => {
  ws.sendMock.mockClear();
});

describe("App", () => {
  it("shows the hand after a state snapshot arrives", () => {
    render(<App />);
    expect(screen.getByText(/Connecting/)).toBeInTheDocument();
    pump(snapshot({ hand: [handCard()] }));
    expect(screen.getByText("Neon Drifter")).toBeInTheDocument();
    expect(screen.getByText(/Your turn/)).toBeInTheDocument();
  });

  it("plays a no-target card on click", () => {
    render(<App />);
    pump(snapshot({ hand: [handCard()] }));
    fireEvent.click(screen.getByText("Neon Drifter"));
    expect(ws.sendMock).toHaveBeenCalledWith({ type: "play", hand: 0 });
  });

  it("enters targeting mode for a CHOSEN track and sends the target", () => {
    render(<App />);
    const foe = boardCard({ serial: 5, name: "Cinder Hound" });
    const track = handCard({
      serial: 20,
      name: "Disco Inferno",
      type: "TRACK",
      is_playable: true,
      needs_target: true,
      legal_targets: [5],
    });
    pump(
      snapshot({
        hand: [track],
        foe: player({ index: 1, board: [foe] }),
        me: player({ index: 0, board: [] }),
      }),
    );
    fireEvent.click(screen.getByText("Disco Inferno"));
    expect(screen.getByText(/Choose a target/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Cinder Hound"));
    expect(ws.sendMock).toHaveBeenCalledWith({
      type: "play",
      hand: 0,
      target: 5,
    });
  });

  it("attacks the station after selecting a creature", () => {
    render(<App />);
    const mine = boardCard({
      serial: 1,
      name: "Neon Drifter",
      can_attack: true,
      attack_targets: [{ kind: "face" }],
    });
    pump(
      snapshot({
        me: player({ index: 0, board: [mine] }),
        hand: [],
      }),
    );
    fireEvent.click(screen.getByText("Neon Drifter"));
    expect(screen.getByText(/Choose an attack target/)).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("rival transmitter"));
    expect(ws.sendMock).toHaveBeenCalledWith({
      type: "attack",
      board: 0,
      target: "face",
    });
  });

  it("sends end_turn with the turn id via the button and the e key", () => {
    render(<App />);
    pump(snapshot());
    fireEvent.click(screen.getByRole("button", { name: "END BROADCAST" }));
    expect(ws.sendMock).toHaveBeenCalledWith({ type: "end_turn", turn: 1 });
    ws.sendMock.mockClear();
    fireEvent.keyDown(window, { key: "e" });
    expect(ws.sendMock).toHaveBeenCalledWith({ type: "end_turn", turn: 1 });
  });

  it("does not send end_turn while the rival is playing", () => {
    render(<App />);
    pump(snapshot({ can_act: false, current: 1 }));
    fireEvent.keyDown(window, { key: "e" });
    expect(ws.sendMock).not.toHaveBeenCalled();
  });

  it("plays hand card 1 with the 1 key", () => {
    render(<App />);
    pump(snapshot({ hand: [handCard()] }));
    fireEvent.keyDown(window, { key: "1" });
    expect(ws.sendMock).toHaveBeenCalledWith({ type: "play", hand: 0 });
  });

  it("shows the win overlay when the game ends", () => {
    render(<App />);
    pump(
      snapshot({
        winner: 0,
        can_act: false,
        status: "Turn 5 | Station 1 | Winner: 0",
      }),
    );
    expect(screen.getByText(/cut the rival off the air/)).toBeInTheDocument();
  });

  it("opens the codex view with the c key", () => {
    render(<App />);
    pump(snapshot());
    fireEvent.keyDown(window, { key: "c" });
    expect(screen.getByRole("button", { name: "CARDS" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "DUEL" }));
    expect(screen.getByText(/Your turn/)).toBeInTheDocument();
  });

  it("opens the changelog when clicking the version and returns via DUEL", () => {
    render(<App />);
    pump(snapshot());
    fireEvent.click(screen.getByRole("button", { name: /v0\.3\.6/ }));
    expect(screen.getByText("VERSION LOG")).toBeInTheDocument();
    expect(screen.getByText("ON THE DIAL — ROADMAP")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "DUEL" }));
    expect(screen.getByText(/Your turn/)).toBeInTheDocument();
  });

  it("applies the summon effect to a card that just aired", () => {
    const { container } = render(<App />);
    pump(snapshot({ turn: 2, current: 1, can_act: false }));
    pump(
      snapshot({
        turn: 2,
        current: 1,
        can_act: false,
        foe: player({ index: 1, board: [boardCard({ serial: 7, name: "Rival Scraper" })] }),
      }),
    );
    const cardEl = container.querySelector(".board-row .card");
    expect(cardEl).toBeInTheDocument();
    expect(cardEl).toHaveClass("fx-summoned");
  });

  it("does not apply the summon effect to cards already on the board", () => {
    const { container } = render(<App />);
    pump(
      snapshot({
        turn: 2,
        current: 1,
        can_act: false,
        foe: player({ index: 1, board: [boardCard({ serial: 7, name: "Rival Scraper" })] }),
      }),
    );
    pump(
      snapshot({
        turn: 2,
        current: 1,
        can_act: false,
        foe: player({ index: 1, board: [boardCard({ serial: 7, name: "Rival Scraper" })] }),
      }),
    );
    const cardEl = container.querySelector(".board-row .card");
    expect(cardEl).not.toHaveClass("fx-summoned");
  });
});
