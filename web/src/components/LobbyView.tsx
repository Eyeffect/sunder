import { useState } from "react";
import { inviteLink, normalizeCode } from "../pvp";
import type { RoomInfo } from "../types";

interface LobbyViewProps {
  room: RoomInfo | null;
  inPvp: boolean;
  onCreate: () => void;
  onJoin: (code: string) => void;
  onCancel: () => void;
  onBack: () => void;
}

/** VERSUS tab: host a room (share code/link) or join one by code. */
export function LobbyView({ room, inPvp, onCreate, onJoin, onCancel, onBack }: LobbyViewProps) {
  const [code, setCode] = useState("");
  const [copied, setCopied] = useState(false);
  const waiting = room?.status === "waiting";

  const copy = async () => {
    if (!room) return;
    try {
      await navigator.clipboard.writeText(inviteLink(room.code));
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  if (inPvp) {
    return (
      <section className="lobby" aria-label="Versus lobby">
        <h2 className="lobby-title">VERSUS</h2>
        <p className="lobby-hint">You're on the air in room {room?.code}.</p>
        <button className="end-turn-btn" type="button" onClick={onBack}>
          BACK TO THE DUEL
        </button>
      </section>
    );
  }

  return (
    <section className="lobby" aria-label="Versus lobby">
      <h2 className="lobby-title">VERSUS</h2>
      {waiting && room ? (
        <div className="lobby-card">
          <div className="lobby-label">ROOM CODE</div>
          <div className="lobby-code" data-testid="room-code">
            {room.code}
          </div>
          <p className="lobby-hint">Waiting for a rival station to tune in…</p>
          <div className="lobby-row">
            <button className="end-turn-btn" type="button" onClick={copy}>
              {copied ? "LINK COPIED" : "COPY INVITE LINK"}
            </button>
            <button className="tab-btn" type="button" onClick={onCancel}>
              CANCEL
            </button>
          </div>
        </div>
      ) : (
        <div className="lobby-grid">
          <div className="lobby-card">
            <div className="lobby-label">HOST</div>
            <p className="lobby-hint">Open a frequency and send the code to a friend.</p>
            <button className="end-turn-btn" type="button" onClick={onCreate}>
              CREATE ROOM
            </button>
          </div>
          <form
            className="lobby-card"
            onSubmit={(e) => {
              e.preventDefault();
              const c = normalizeCode(code);
              if (c) onJoin(c);
            }}
          >
            <label className="lobby-label" htmlFor="room-code-input">
              JOIN
            </label>
            <input
              id="room-code-input"
              className="lobby-input"
              value={code}
              onChange={(e) => setCode(normalizeCode(e.target.value))}
              placeholder="ABC234"
              maxLength={12}
              autoComplete="off"
              spellCheck={false}
            />
            <button className="end-turn-btn" type="submit" disabled={!normalizeCode(code)}>
              JOIN ROOM
            </button>
          </form>
        </div>
      )}
      <p className="lobby-foot">
        Turns are timed in versus. Leaving or closing the tab for too long forfeits.
      </p>
    </section>
  );
}
