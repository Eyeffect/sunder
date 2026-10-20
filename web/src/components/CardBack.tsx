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
  const cls = `card-back card-back--${s.id}`;
  const style = {
    "--sleeve-ink": s.css.ink,
    "--sleeve-primary": s.css.ink,
    "--sleeve-glow": s.css.glow,
    "--sleeve-paper": s.css.paper,
  } as CSSProperties;
  return (
    <div className={cls} style={style} aria-hidden="true">
      <CardBackArt sleeve={s} />
      {secret && <span className="card-back-secret">?</span>}
    </div>
  );
}
