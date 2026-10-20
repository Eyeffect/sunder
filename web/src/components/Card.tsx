import type { CSSProperties } from "react";
import { useEffect, useRef, useState } from "react";
import { planeMeta } from "../planes";
import { CardBack } from "./CardBack";

export interface CardLike {
  serial?: number;
  hidden?: boolean;
  type?: string | null;
  name: string;
  keywords?: string[];
  tags?: string[];
  tagMeanings?: Record<string, string>;
  is_token?: boolean;
  cost?: number;
  atk?: number;
  def?: number;
  rules?: string;
  plane?: string;
  rarity?: string;
  fuse?: number | null;
  fuse_ticks?: number;
}

export function ClampedText({
  text,
  className = "card-rules",
}: {
  text: string;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [clipped, setClipped] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const check = () => setClipped(el.scrollHeight > el.clientHeight + 1);
    check();
    const ro =
      typeof ResizeObserver === "undefined" ? null : new ResizeObserver(check);
    ro?.observe(el);
    document.fonts?.ready.then(check).catch(() => {});
    return () => ro?.disconnect();
  }, [text]);

  return (
    <div className={className} data-clipped={clipped ? "true" : undefined} ref={ref}>
      {text}
    </div>
  );
}

export function CardRules({ text, className }: { text: string; className?: string }) {
  return <ClampedText text={text} className={className} />;
}

export function CardBadge({ plane, rarity }: { plane?: string; rarity?: string }) {
  const meta = planeMeta(plane);
  const style = {
    "--rarity-color": rarity ? `var(--${rarity.toLowerCase()})` : undefined,
  } as CSSProperties;
  return (
    <span className="card-badge" style={style}>
      <span className="badge-edition">
        <span className="plane-code">{meta.code}</span>
        <span className="plane-name">{meta.label}</span>
      </span>
      {rarity && (
        <span
          className="badge-rarity"
          role="img"
          aria-label={`Rarity: ${rarity}`}
          title={`Rarity: ${rarity}`}
        >
          {rarity}
        </span>
      )}
    </span>
  );
}

export function CostBars({ cost, playable }: { cost?: number; playable?: boolean }) {
  const bars = [1, 2, 3, 4, 5];
  const filled = Math.min(5, Math.ceil(((cost ?? 0) / 10) * 5) || 1);
  const state = playable === undefined ? "" : playable ? " playable" : " unplayable";
  return (
    <div
      className={"cost-bars" + state}
      title={`Cost ${cost ?? "?"}${playable === undefined ? "" : playable ? " — playable" : " — not playable"}`}
    >
      {bars.map((b) => (
        <span
          key={b}
          className={"cost-bar" + (b <= filled ? " on" : "")}
          style={{ height: `${b * 2.6 + 4}px` }}
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
          {Array.from({ length: max }).map((_, i) => (
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
  playable?: boolean;
  sleeve?: string;
  fxHurt?: boolean;
  fxRevealed?: boolean;
  fxSummoned?: boolean;
}

export function Card({
  card,
  onClick,
  onHover,
  onLeave,
  className,
  size = "md",
  playable,
  sleeve,
  fxHurt,
  fxRevealed,
  fxSummoned,
}: CardProps) {
  const cls = [
    "card",
    `size-${size}`,
    card.hidden ? "card-hidden" : `card-${(card.type ?? "unknown").toLowerCase()}`,
    card.is_token ? "card-token" : "",
    className ?? "",
    fxHurt ? "fx-hurt" : "",
    fxRevealed ? "fx-revealed" : "",
    fxSummoned ? "fx-summoned" : "",
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
          <span className="card-watermark" aria-hidden="true">
            {meta.code}
          </span>
          <div className="card-top">
            <CostBars cost={card.cost} playable={playable} />
            <CardBadge plane={card.plane} rarity={card.rarity} />
          </div>
          <div className="card-name">{card.name}</div>
          {typeLine && <div className="card-type">{typeLine}</div>}
          {card.tags && card.tags.length > 0 && (
            <div className="card-tags">
              {card.tags.map((t) => (
                <span
                  key={t}
                  className="tag-chip"
                  title={card.tagMeanings?.[t] ?? `#${t}`}
                >
                  {t}
                </span>
              ))}
            </div>
          )}
          {card.fuse != null && (
            <div className="card-fuse">
              FUSE {card.fuse_ticks ?? 0}/{card.fuse}
            </div>
          )}
          {card.rules && <CardRules text={card.rules} />}
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
