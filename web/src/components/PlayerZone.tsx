import type { CSSProperties } from "react";
import type { BoardCard, PlayerState } from "../types";
import { sleeveOf } from "../sleeves";
import { Card, VuMeter } from "./Card";

export function DeckStack({
  sleeve,
  count,
  size = "compact",
}: {
  sleeve: string;
  count: number;
  size?: "compact" | "board";
}) {
  const style = { "--accent": sleeveOf(sleeve).css.ink } as CSSProperties;
  return (
    <div className={`deck-stack ${size}`} title={`${count} cards in deck`}>
      <div className="deck-card back-3" />
      <div className="deck-card back-2" />
      <div className="deck-card back-1" style={style}>
        <span className="deck-icon">◉</span>
      </div>
      <span className="deck-count">{count}</span>
    </div>
  );
}

export interface FxState {
  hurt: number[];
  revealed: number[];
  summoned: number[];
}

interface BoardRowProps {
  player: PlayerState;
  targetable: Set<number>;
  selectedSerial?: number | null;
  onCardClick?: (card: BoardCard) => void;
  onHover?: (card: BoardCard | null) => void;
  fx: FxState;
}

const SLOTS = 6;

export function BoardRow({
  player,
  targetable,
  selectedSerial,
  onCardClick,
  onHover,
  fx,
}: BoardRowProps) {
  const emptySlots = Math.max(0, SLOTS - player.board.length);
  return (
    <div className="board-row-wrap">
      <div className="board-row">
        {player.board.map((card) => {
          const cls = [
            targetable.has(card.serial) ? "card-targetable" : "",
            selectedSerial === card.serial ? "card-selected" : "",
          ]
            .filter(Boolean)
            .join(" ");
          return (
            <Card
              key={card.serial}
              card={card}
              size="lg"
              className={cls}
              sleeve={player.sleeve}
              onClick={() => onCardClick?.(card)}
              onHover={() => onHover?.(card)}
              onLeave={() => onHover?.(null)}
              fxHurt={fx.hurt.includes(card.serial)}
              fxRevealed={fx.revealed.includes(card.serial)}
              fxSummoned={fx.summoned.includes(card.serial)}
            />
          );
        })}
        {Array.from({ length: emptySlots }).map((_, i) => (
          <div key={`slot${i}`} className="slot empty size-lg" />
        ))}
      </div>
      <DeckStack sleeve={player.sleeve} count={player.playlist_count} size="board" />
    </div>
  );
}

interface PlayerZoneProps {
  title: string;
  player: PlayerState;
  mine?: boolean;
  canEndTurn?: boolean;
  onEndTurn?: () => void;
  targetableFace?: boolean;
  onClick?: () => void;
}

export function PlayerZone({
  title,
  player,
  mine = false,
  canEndTurn = false,
  onEndTurn,
  targetableFace = false,
  onClick,
}: PlayerZoneProps) {
  return (
    <div
      className={`side-panel ${mine ? "player" : "opponent"}${targetableFace ? " side-panel-face-targetable" : ""}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      aria-label={onClick ? "rival transmitter" : undefined}
    >
      <div className={`avatar-frame ${mine ? "you" : "opp"}`} aria-hidden="true">
        ◉
      </div>
      <div className="side-info">
        <div className="side-name">{title}</div>
        <VuMeter value={player.signal} max={player.max_signal} colorVar={mine ? "--amber" : "--magenta"} />
        <div className="side-meta">
          <span>HAND {player.hand_count}</span>
          <span className="bandwidth">
            <span className="bw-label">BANDWIDTH</span>
            <span className="bw-cells">
              {Array.from({ length: Math.max(0, player.max_bandwidth) }).map((_, i) => (
                <span key={i} className={i < player.bandwidth ? "on" : ""} />
              ))}
            </span>
            <span className="bw-readout">
              {player.bandwidth}/{player.max_bandwidth}
            </span>
          </span>
        </div>
      </div>
      {mine && (
        <button className="end-turn-btn" onClick={onEndTurn} disabled={!canEndTurn} type="button">
          END BROADCAST
        </button>
      )}
    </div>
  );
}
