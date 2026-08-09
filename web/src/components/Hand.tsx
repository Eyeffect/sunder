import type { CSSProperties } from "react";
import type { HandCard } from "../types";
import { Card } from "./Card";

interface HandProps {
  hand: HandCard[];
  activeSerial?: number | null;
  onCardClick?: (card: HandCard) => void;
  onHover?: (card: HandCard | null) => void;
}

export function Hand({ hand, activeSerial, onCardClick, onHover }: HandProps) {
  const n = hand.length;
  const fan = n > 0;
  const center = (n - 1) / 2;
  const scale = Math.min(1, 6 / n);
  const CARD_W = 118;
  const FIT = 760;
  const overlap =
    n <= 1
      ? 0
      : Math.min(48, Math.max(16, Math.ceil((n * CARD_W - FIT) / (n - 1))));
  const rowStyle = { "--overlap": `${overlap}px` } as CSSProperties;
  return (
    <div className={`hand-row${fan ? " fan" : ""}`} style={fan ? rowStyle : undefined}>
      {hand.length === 0 && <span className="zone-empty">— no cards —</span>}
      {hand.map((card, i) => {
        const cls = [
          card.is_playable ? "hand-playable" : "hand-busy",
          activeSerial === card.serial ? "hand-active" : "",
        ]
          .filter(Boolean)
          .join(" ");
        const rot = fan ? (i - center) * 3 * scale : 0;
        const lift = fan ? Math.abs(i - center) * 3 * scale : 0;
        const style = { "--rot": `${rot}deg`, "--lift": `${lift}px` } as CSSProperties;
        return (
          <div key={card.serial} className="hand-card-wrap" style={style}>
            <Card
              card={card}
              size="md"
              className={`hand-card ${cls}`}
              onClick={() => onCardClick?.(card)}
              onHover={() => onHover?.(card)}
              onLeave={() => onHover?.(null)}
            />
          </div>
        );
      })}
    </div>
  );
}
