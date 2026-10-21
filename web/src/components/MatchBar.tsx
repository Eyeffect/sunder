import { useEffect, useState } from "react";
import type { MatchMeta } from "../types";

interface MatchBarProps {
  match: MatchMeta;
  /** ms epoch when the current turn clock expires (client-side estimate). */
  deadline: number | null;
  myTurn: boolean;
  gameOver: boolean;
  onConcede: () => void;
}

/** PvP strip above the board: room code, rival link status, turn clock, concede. */
export function MatchBar({ match, deadline, myTurn, gameOver, onConcede }: MatchBarProps) {
  const [now, setNow] = useState(() => Date.now());
  const [confirm, setConfirm] = useState(false);

  useEffect(() => {
    if (deadline === null || gameOver) return;
    const id = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(id);
  }, [deadline, gameOver]);

  const secs = deadline === null ? null : Math.max(0, Math.ceil((deadline - now) / 1000));
  const low = secs !== null && secs <= 10;

  return (
    <div className="match-bar" role="group" aria-label="Match status">
      <span className="match-code">ROOM {match.code}</span>
      <span className={`match-link ${match.opponent_connected ? "on" : "off"}`}>
        {match.opponent_connected ? "RIVAL ON AIR" : "RIVAL SIGNAL LOST…"}
      </span>
      {secs !== null && !gameOver && (
        <span
          className={`match-clock ${low ? "low" : ""}`}
          aria-label={`${myTurn ? "Your" : "Rival"} turn, ${secs} seconds left`}
        >
          {myTurn ? "YOUR TURN" : "RIVAL"} {secs}s
        </span>
      )}
      {!gameOver &&
        (confirm ? (
          <span className="match-confirm">
            <button className="tab-btn danger" type="button" onClick={onConcede}>
              YES, CONCEDE
            </button>
            <button className="tab-btn" type="button" onClick={() => setConfirm(false)}>
              KEEP PLAYING
            </button>
          </span>
        ) : (
          <button className="tab-btn" type="button" onClick={() => setConfirm(true)}>
            CONCEDE
          </button>
        ))}
    </div>
  );
}
