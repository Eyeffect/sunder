import type { Snapshot } from "../types";

export interface CardInfo {
  name: string;
  hidden?: boolean;
  rules?: string;
  flavor?: string;
  keywords?: string[];
}

export function Inspector({ card }: { card: CardInfo | null }) {
  if (!card) {
    return (
      <div className="inspector inspector-empty">
        <div className="inspector-header">INSPECTOR</div>
        Hover a card to inspect it.
      </div>
    );
  }
  const masked = card.hidden && card.name === "???";
  return (
    <div className="inspector">
      <div className="inspector-header">INSPECTOR</div>
      <div className="inspector-name">{masked ? "??? (hidden B-SIDE)" : card.name}</div>
      {card.keywords && card.keywords.length > 0 && (
        <div className="inspector-kw">{card.keywords.join(" ")}</div>
      )}
      {!masked && card.rules && <div className="inspector-rules">{card.rules}</div>}
      {!masked && card.flavor && (
        <div className="inspector-flavor">“{card.flavor}”</div>
      )}
    </div>
  );
}

export function EndGameOverlay({
  snapshot,
  onRestart,
}: {
  snapshot: Snapshot;
  onRestart: () => void;
}) {
  const won = snapshot.winner === snapshot.viewer;
  return (
    <div className="overlay">
      <div className={`overlay-card ${won ? "overlay-win" : "overlay-loss"}`}>
        <h1>{won ? "You cut the rival off the air." : "You were cut off the air."}</h1>
        <p>{snapshot.status}</p>
        <button className="btn btn-primary" onClick={onRestart}>
          Play again
        </button>
      </div>
    </div>
  );
}
