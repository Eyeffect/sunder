import type { ClientMsg, MatchMeta, RoomInfo, ServerMsg, Snapshot } from "./types";

export class GameSocket {
  private ws: WebSocket | null = null;
  private queue: ClientMsg[] = [];
  private closing = false;
  private readonly url: string;

  onState: (snapshot: Snapshot, match?: MatchMeta) => void = () => {};
  onError: (message: string) => void = () => {};
  onRoom: (room: RoomInfo) => void = () => {};
  onRoomClosed: (reason: string) => void = () => {};
  onOpen: () => void = () => {};

  constructor() {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    this.url = `${proto}://${window.location.host}/ws`;
  }

  connect(): void {
    this.closing = false;
    this.ws = new WebSocket(this.url);
    this.ws.onopen = () => {
      this.flush();
      this.onOpen();
    };
    this.ws.onmessage = (ev) => {
      let msg: ServerMsg;
      try {
        msg = JSON.parse(ev.data as string);
      } catch {
        return;
      }
      if (msg.type === "state" && msg.snapshot) this.onState(msg.snapshot, msg.match);
      else if (msg.type === "error" && msg.message) this.onError(msg.message);
      else if (msg.type === "room" && msg.code && msg.status) {
        this.onRoom({
          mode: "pvp",
          code: msg.code,
          seat: msg.seat ?? null,
          token: msg.token ?? null,
          status: msg.status,
        });
      } else if (msg.type === "room_closed") this.onRoomClosed(msg.reason ?? "");
    };
    this.ws.onclose = () => {
      this.ws = null;
      if (!this.closing) {
        setTimeout(() => this.connect(), 1000);
      }
    };
  }

  send(msg: ClientMsg): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    } else if (this.ws) {
      this.queue.push(msg);
    }
  }

  private flush(): void {
    while (this.queue.length) {
      const msg = this.queue.shift();
      if (msg) this.ws?.send(JSON.stringify(msg));
    }
  }

  close(): void {
    this.closing = true;
    this.ws?.close();
    this.ws = null;
    this.queue = [];
  }
}
