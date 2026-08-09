import type { CSSProperties } from "react";
import { planeMeta } from "../planes";
import { CardBack } from "./CardBack";

export interface CardLike {
  serial?: number;
  hidden?: boolean;
  type?: string | null;
  name: string;
  keywords?: string[];
  is_token?: boolean;
  cost?: number;
  atk?: number;
  def?: number;
  rules?: string;
  plane?: string;
  fuse?: number | null;
  fuse_ticks?: number;
}

export function CostBars({ cost }: { cost?: number }) {
  const bars = [1, 2, 3, 4, 5];
  const filled = Math.min(5, Math.ceil(((cost ?? 0) / 10) * 5) || 1);
  return (
    <div className="cost-bars" title={`Cost ${cost ?? "?"}`}>
      {bars.map((b) => (
        <span
          key={b}
          className={"cost-bar" + (b <= filled ? " on" : "")}
          style={{ height: `${b * 3 + 4}px` }}
        />
      ))}
      <span className="cost-num">{cost ?? "—"}</span>
    </div>
  );
}

export function VuMeter({
  value,
  max,
  colorVar = "--amber",
}: {
  value: number;
  max: number;
  colorVar?: string;
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const critical = pct <= 25;
  return (
    <div
      className="vu-wrap"
      role="meter"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-label="signal"
    >
      <div className="vu-track">
        <div
          className={"vu-fill" + (critical ? " critical" : "")}
          style={{ width: `${pct}%`, background: critical ? "var(--danger)" : `var(${colorVar})` }}
        />
        <div className="vu-ticks">
          {Array.from({ length: 20 }).map((_, i) => (
            <span key={i} />
          ))}
        </div>
      </div>
      <span className="vu-readout">
        {value}/{max}
      </span>
    </div>
  );
}

interface CardProps {
  card: CardLike;
  onClick?: () => void;
  onHover?: () => void;
  onLeave?: () => void;
  className?: string;
  size?: "sm" | "md" | "lg";
  sleeve?: string;
  fxHurt?: boolean;
  fxRevealed?: boolean;
}

export function Card({
  card,
  onClick,
  onHover,
  onLeave,
  className,
  size = "md",
  sleeve,
  fxHurt,
  fxRevealed,
}: CardProps) {
  const cls = [
    "card",
    `size-${size}`,
    card.hidden ? "card-hidden" : `card-${(card.type ?? "unknown").toLowerCase()}`,
    card.is_token ? "card-token" : "",
    className ?? "",
    fxHurt ? "fx-hurt" : "",
    fxRevealed ? "fx-revealed" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const meta = planeMeta(card.plane);
  const style = { "--plane-color": meta.color } as CSSProperties;

  const typeLine = [
    card.type ?? "",
    card.keywords && card.keywords.length > 0 ? card.keywords.join(", ") : "",
  ]
    .filter(Boolean)
    .join(" — ");

  return (
    <div
      className={cls}
      style={style}
      onClick={onClick}
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
    >
      {card.hidden ? (
        <div className="card-mystery">
          <CardBack sleeve={sleeve ?? "default"} secret />
          <span className="mystery-label">B-SIDE</span>
        </div>
      ) : (
        <>
          <div className="card-plane-strip" />
          <div className="card-top">
            <CostBars cost={card.cost} />
            <span className="card-plane-tag">{meta.label}</span>
          </div>
          <div className="card-name">{card.name}</div>
          {typeLine && <div className="card-type">{typeLine}</div>}
          {card.fuse != null && (
            <div className="card-fuse">
              FUSE {card.fuse_ticks ?? 0}/{card.fuse}
            </div>
          )}
          {card.rules && <div className="card-rules">{card.rules}</div>}
          {card.type === "BROADCAST" && card.atk != null && (
            <div className="card-stats">
              <span className="stat atk">{card.atk}</span>
              <span className="stat-div">/</span>
              <span className="stat def">{card.def}</span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
