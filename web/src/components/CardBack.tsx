import type { CSSProperties } from "react";
import type { Sleeve } from "../sleeves";
import { sleeveOf } from "../sleeves";
import { CardBackArt } from "../backPatterns";

export function CardBack({
  sleeve,
  secret = false,
}: {
  sleeve: string | Sleeve;
  secret?: boolean;
}) {
  const s = typeof sleeve === "string" ? sleeveOf(sleeve) : sleeve;
  const cls = `card-back card-back--${s.pattern}`;
  const style = {
    "--sleeve-primary": s.css.ink,
    "--sleeve-glow": s.css.glow,
    "--sleeve-paper": s.css.paper,
  } as CSSProperties;
  return (
    <div className={cls} style={style} aria-hidden="true">
      <CardBackArt sleeve={s} />
      {s.emblem && <span className="card-back-emblem">{secret ? "?" : s.emblem}</span>}
    </div>
  );
}
