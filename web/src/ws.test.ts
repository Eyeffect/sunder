import { afterEach, describe, expect, it, vi } from "vitest";
import { GameSocket } from "./ws";

class FakeWS {
  static instances: FakeWS[] = [];
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 3;
  readyState = FakeWS.CONNECTING;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  constructor(_url: string) {
    FakeWS.instances.push(this);
  }
  send(data: string): void {
    this.sent.push(data);
  }
  close(): void {
    this.readyState = FakeWS.CLOSED;
    this.onclose?.();
  }
}

vi.stubGlobal("WebSocket", FakeWS);

afterEach(() => {
  vi.useRealTimers();
  FakeWS.instances = [];
});

describe("GameSocket", () => {
  it("queues messages until the socket opens, then flushes", () => {
    vi.useFakeTimers();
    const sock = new GameSocket();
    const onOpen = vi.fn();
    sock.onOpen = onOpen;
    sock.connect();
    const fake = FakeWS.instances.at(-1)!;
    sock.send({ type: "start" });
    expect(fake.sent).toEqual([]); // still CONNECTING
    fake.readyState = FakeWS.OPEN;
    fake.onopen?.();
    expect(fake.sent).toEqual([JSON.stringify({ type: "start" })]);
    expect(onOpen).toHaveBeenCalled();
    sock.send({ type: "end_turn" });
    expect(fake.sent).toHaveLength(2);
    sock.close();
  });

  it("sends immediately once open", () => {
    vi.useFakeTimers();
    const sock = new GameSocket();
    sock.connect();
    const fake = FakeWS.instances.at(-1)!;
    fake.readyState = FakeWS.OPEN;
    sock.send({ type: "ping" });
    expect(fake.sent).toEqual([JSON.stringify({ type: "ping" })]);
    sock.close();
  });

  it("dispatches state snapshots from the server", () => {
    vi.useFakeTimers();
    const sock = new GameSocket();
    const onState = vi.fn();
    sock.onState = onState;
    sock.connect();
    const fake = FakeWS.instances.at(-1)!;
    fake.onmessage?.({ data: JSON.stringify({ type: "state", snapshot: { turn: 1 } }) });
    expect(onState).toHaveBeenCalledWith({ turn: 1 });
    sock.close();
  });

  it("does not reconnect after an explicit close", () => {
    vi.useFakeTimers();
    const sock = new GameSocket();
    sock.connect();
    sock.close();
    vi.runAllTimers();
    expect(FakeWS.instances).toHaveLength(1);
  });
});
