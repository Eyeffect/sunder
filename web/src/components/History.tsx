import { useState, type CSSProperties, type MouseEvent } from "react";
import { createPortal } from "react-dom";
import { planeMeta } from "../planes";
import type { HistoryCard, HistoryEvent } from "../types";

const MAX_ICONS = 12;

function glyph(kind: HistoryEvent["kind"]): string {
  switch (kind) {
    case "attack":
    case "face_attack":
      return "⚔";
    case "damage":
      return "⚡";
    case "death":
      return "☠";
    case "reveal":
      return "◉";
    case "draw":
      return "⬇";
    case "summon":
      return "✦";
    case "win":
      return "★";
    default:
      return "•";
  }
}

function badgeClass(kind: HistoryEvent["kind"]): string {
  if (kind === "face_attack") return "face-attack";
  if (kind === "play") return "play";
  if (kind === "attack") return "attack";
  if (kind === "damage") return "damage";
  if (kind === "death") return "death";
  if (kind === "reveal") return "reveal";
  if (kind === "draw") return "draw";
  if (kind === "summon") return "summon";
  if (kind === "win") return "win";
  return "system";
}

function typeGlyph(type: HistoryCard["type"]): string {
  if (type === "BROADCAST") return "◈";
  if (type === "TRACK") return "➤";
  if (type === "LOOP") return "◎";
  return "?";
}

function MiniCard({ card }: { card: HistoryCard }) {
  const meta = planeMeta(card.plane);
  const style = { "--plane-color": meta.color } as CSSProperties;
  return (
    <div className="mini-card" style={style}>
      <div className="mini-strip" />
      <div className="mini-type">{typeGlyph(card.type)}</div>
      <div className="mini-cost">{card.cost ?? "?"}</div>
    </div>
  );
}

interface Tip {
  text: string;
  cardName?: string;
  x: number;
  y: number;
}

export function History({ history }: { history: HistoryEvent[] }) {
  const [tip, setTip] = useState<Tip | null>(null);
  const events = history
    .filter((e) => (e.kind as string) !== "turn")
    .slice(-MAX_ICONS)
    .reverse();

  const showTip =
    (ev: HistoryEvent) =>
    (e: MouseEvent<HTMLDivElement>) =>
      setTip({
        text: ev.text,
        cardName: ev.card?.name,
        x: Math.min(e.clientX + 14, (window.innerWidth || 0) - 300),
        y: Math.min(e.clientY + 16, (window.innerHeight || 0) - 80),
      });

  return (
    <div className="history" aria-label="game history">
      {events.length === 0 && <div className="history-empty">—</div>}
      {events.map((ev, i) => (
        <div
          key={i}
          className={`history-badge ${badgeClass(ev.kind)}`}
          aria-label={ev.text}
          onMouseEnter={showTip(ev)}
          onMouseLeave={() => setTip(null)}
        >
          {ev.kind === "play" && ev.card ? (
            <MiniCard card={ev.card} />
          ) : (
            <span className="history-glyph">{glyph(ev.kind)}</span>
          )}
        </div>
      ))}
      {tip &&
        createPortal(
          <div className="history-tip" style={{ left: tip.x, top: tip.y }}>
            {tip.cardName && <strong>{tip.cardName}</strong>}
            {tip.cardName ? " — " : ""}
            {tip.text}
          </div>,
          document.body,
        )}
    </div>
  );
}
