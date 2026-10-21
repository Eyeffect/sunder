import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type {
  BoardCard,
  HandCard,
  MatchMeta,
  PlayerState,
  RoomInfo,
  Snapshot,
} from "./types";

const ws = vi.hoisted(() => {
  const sendMock = vi.fn();
  class GameSocket {
    static last: GameSocket | null = null;
    onState: (s: Snapshot, m?: MatchMeta) => void = () => {};
    onError: (m: string) => void = () => {};
    onOpen: () => void = () => {};
    onRoom: (r: RoomInfo) => void = () => {};
    onRoomClosed: (reason: string) => void = () => {};
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

const storage = vi.hoisted(() => {
  const data = new Map<string, string>();
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => {
      data.set(key, value);
    },
    removeItem: (key: string) => {
      data.delete(key);
    },
    clear: () => data.clear(),
  };
});

vi.stubGlobal("localStorage", storage);

const session = vi.hoisted(() => {
  const data = new Map<string, string>();
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => void data.set(key, value),
    removeItem: (key: string) => void data.delete(key),
    clear: () => data.clear(),
  };
});
vi.stubGlobal("sessionStorage", session);

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
  storage.clear();
  session.clear();
  window.history.replaceState(null, "", "/");
});

const pvpMeta = (o: Partial<MatchMeta> = {}): MatchMeta => ({
  mode: "pvp",
  code: "ABC234",
  seat: 0,
  opponent_connected: true,
  turn_seconds: 75,
  turn_remaining: 60,
  ...o,
});

function pumpPvp(snap: Snapshot, meta: MatchMeta = pvpMeta()): void {
  const sock = ws.GameSocket.last;
  act(() => sock?.onState(snap, meta));
}

function room(o: Partial<RoomInfo> = {}): RoomInfo {
  return { mode: "pvp", code: "ABC234", seat: 0, token: "tok", status: "live", ...o };
}

describe("App — versus", () => {
  it("starts a practice match on connect by default", () => {
    render(<App />);
    act(() => ws.GameSocket.last?.onOpen());
    expect(ws.sendMock).toHaveBeenCalledWith({ type: "start" });
  });

  it("resumes a saved PvP seat instead of starting", () => {
    session.setItem("sunder-pvp", JSON.stringify({ code: "ABC234", token: "tok" }));
    render(<App />);
    act(() => ws.GameSocket.last?.onOpen());
    expect(ws.sendMock).toHaveBeenCalledWith({ type: "resume", code: "ABC234", token: "tok" });
    expect(ws.sendMock).not.toHaveBeenCalledWith({ type: "start" });
  });

  it("joins the room from an invite link", () => {
    window.history.replaceState(null, "", "/?room=abc234");
    render(<App />);
    act(() => ws.GameSocket.last?.onOpen());
    expect(ws.sendMock).toHaveBeenCalledWith({ type: "join_room", code: "ABC234" });
  });

  it("falls back to practice when a stale resume fails during boot", () => {
    session.setItem("sunder-pvp", JSON.stringify({ code: "ABC234", token: "old" }));
    render(<App />);
    const sock = ws.GameSocket.last!;
    act(() => sock.onOpen());
    act(() => sock.onError("that match is no longer running"));
    expect(ws.sendMock).toHaveBeenCalledWith({ type: "start" });
    expect(session.getItem("sunder-pvp")).toBeNull();
  });

  it("hosts from the VERSUS tab and shows the code", () => {
    render(<App />);
    pump(snapshot());
    fireEvent.click(screen.getByRole("button", { name: "VERSUS" }));
    fireEvent.click(screen.getByRole("button", { name: "CREATE ROOM" }));
    expect(ws.sendMock).toHaveBeenCalledWith({ type: "create_room" });
    act(() => ws.GameSocket.last?.onRoom(room({ seat: null, token: null, status: "waiting" })));
    expect(screen.getByTestId("room-code")).toHaveTextContent("ABC234");
  });

  it("cancelling a hosted room drops back to practice", () => {
    render(<App />);
    pump(snapshot());
    const sock = ws.GameSocket.last!;
    act(() => sock.onRoom(room({ seat: null, token: null, status: "waiting" })));
    ws.sendMock.mockClear();
    act(() => sock.onRoomClosed("left"));
    expect(ws.sendMock).toHaveBeenCalledWith({ type: "start" });
  });

  it("saves the seat token and jumps to the duel when the match goes live", () => {
    render(<App />);
    pump(snapshot());
    fireEvent.click(screen.getByRole("button", { name: "VERSUS" }));
    act(() => ws.GameSocket.last?.onRoom(room()));
    pumpPvp(snapshot());
    expect(JSON.parse(session.getItem("sunder-pvp")!)).toEqual({ code: "ABC234", token: "tok" });
    expect(screen.getByText("ROOM ABC234")).toBeInTheDocument();
    expect(screen.getByText("END BROADCAST")).toBeInTheDocument();
  });

  it("concedes after confirmation", () => {
    render(<App />);
    pumpPvp(snapshot());
    fireEvent.click(screen.getByRole("button", { name: "CONCEDE" }));
    fireEvent.click(screen.getByRole("button", { name: "YES, CONCEDE" }));
    expect(ws.sendMock).toHaveBeenCalledWith({ type: "concede" });
  });

  it("explains how a PvP match ended and offers practice", () => {
    session.setItem("sunder-pvp", JSON.stringify({ code: "ABC234", token: "tok" }));
    render(<App />);
    pumpPvp(snapshot({ winner: 0, can_act: false, end_reason: "concede" }));
    expect(screen.getByText("The rival conceded.")).toBeInTheDocument();
    expect(session.getItem("sunder-pvp")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Practice vs the bot" }));
    expect(ws.sendMock).toHaveBeenCalledWith({ type: "restart" });
  });

  it("shows no match bar in practice games", () => {
    render(<App />);
    pump(snapshot());
    expect(screen.queryByText(/ROOM /)).not.toBeInTheDocument();
  });
});

describe("App", () => {
  it("shows the hand after a state snapshot arrives", () => {
    render(<App />);
    expect(screen.getByText(/Connecting/)).toBeInTheDocument();
    pump(snapshot({ hand: [handCard()] }));
    expect(screen.getByText("Neon Drifter")).toBeInTheDocument();
    expect(screen.getByText(/Your turn/)).toBeInTheDocument();
  });

  it("picks a profile icon from the station avatar", () => {
    render(<App />);
    pump(
      snapshot({
        me: player({
          index: 0,
          avatar: "frequency",
          avatar_glyph: "◉",
          sleeve_ink: "amber",
        }),
      }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Choose profile icon" }));
    expect(screen.getByRole("dialog", { name: "Choose profile icon" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Cinderworks/ }));
    expect(ws.sendMock).toHaveBeenCalledWith({ type: "set_avatar", avatar: "cinder" });
    expect(localStorage.getItem("sunder-avatar")).toBe("cinder");
  });

  it("restores the saved profile icon once the first state arrives", () => {
    localStorage.setItem("sunder-avatar", "vhs");
    render(<App />);
    const sock = ws.GameSocket.last;
    act(() => sock?.onOpen());
    // cosmetics follow the first snapshot so they reach the right seat
    // (practice, resumed PvP, or a freshly joined room)
    expect(ws.sendMock).not.toHaveBeenCalledWith({ type: "set_avatar", avatar: "vhs" });
    pump(snapshot());
    expect(ws.sendMock).toHaveBeenCalledWith({ type: "set_avatar", avatar: "vhs" });
  });

  it("signals playability on the hand cost bars", () => {
    render(<App />);
    pump(
      snapshot({
        hand: [
          handCard({ serial: 11, is_playable: true }),
          handCard({ serial: 12, name: "Final Wave", cost: 6, is_playable: false }),
        ],
      }),
    );
    expect(screen.getByTitle("Cost 3 — playable")).toBeInTheDocument();
    expect(screen.getByTitle("Cost 6 — not playable")).toBeInTheDocument();
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
    const { container } = render(<App />);
    pump(snapshot());
    const bg = () => container.querySelector(".shader-bg") as HTMLElement;
    expect(bg().dataset.codex).toBe("false");
    fireEvent.keyDown(window, { key: "c" });
    expect(screen.getByRole("button", { name: "CARDS" })).toBeInTheDocument();
    expect(bg().dataset.codex).toBe("true");
    fireEvent.click(screen.getByRole("button", { name: "DUEL" }));
    expect(screen.getByText(/Your turn/)).toBeInTheDocument();
    expect(bg().dataset.codex).toBe("false");
  });

  it("opens the changelog when clicking the version and returns via DUEL", () => {
    render(<App />);
    pump(snapshot());
    fireEvent.click(screen.getByRole("button", { name: /^v\d+\.\d+/ }));
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
