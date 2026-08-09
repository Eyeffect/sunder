import type { CSSProperties } from "react";
import { sleeveOf, type Sleeve } from "../sleeves";

export function CardBack({
  sleeve,
  secret = false,
}: {
  sleeve: string | Sleeve;
  secret?: boolean;
}) {
  const s = typeof sleeve === "string" ? sleeveOf(sleeve) : sleeve;
  const cls = s.asset
    ? "card-back card-back--asset"
    : `card-back card-back--${s.pattern}`;
  const style = {
    "--sleeve-primary": s.colors.primary,
    "--sleeve-glow": s.colors.glow,
  } as CSSProperties;
  return (
    <div className={cls} style={style} aria-hidden="true">
      {s.asset ? (
        <img src={s.asset} alt="" />
      ) : (
        <span className="card-back-emblem">{secret ? "?" : s.emblem}</span>
      )}
    </div>
  );
}
