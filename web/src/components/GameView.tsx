import { useEffect, useRef, useState } from "react";
import type { BoardCard, HandCard, Mode, Snapshot } from "../types";
import { Hand } from "./Hand";
import { History } from "./History";
import { EndGameOverlay } from "./Overlays";
import { BoardRow, PlayerZone, type FxState } from "./PlayerZone";

interface GameViewProps {
  snapshot: Snapshot;
  mode: Mode;
  status: string;
  onPlayCard: (card: HandCard) => void;
  onClickMine: (card: BoardCard) => void;
  onClickFoe: (card: BoardCard) => void;
  onClickFace: () => void;
  onEndTurn: () => void;
  onRestart: () => void;
}

export function GameView(props: GameViewProps) {
  const { snapshot, mode, status } = props;
  const [fx, setFx] = useState<FxState>({ hurt: [], revealed: [] });
  const prevRef = useRef<Snapshot | null>(null);

  useEffect(() => {
    const prev = prevRef.current;
    if (prev) {
      const cur = new Map<number, BoardCard>();
      for (const p of [snapshot.me, snapshot.foe]) {
        for (const c of p.board) cur.set(c.serial, c);
      }
      const hurt: number[] = [];
      const revealed: number[] = [];
      for (const p of [prev.me, prev.foe]) {
        for (const c of p.board) {
          const now = cur.get(c.serial);
          if (!now) continue;
          if (c.hidden && !now.hidden) revealed.push(c.serial);
          if ((c.damage ?? 0) < (now.damage ?? 0) || (c.def ?? 0) > (now.def ?? 0)) {
            hurt.push(c.serial);
          }
        }
      }
      if (hurt.length || revealed.length) setFx({ hurt, revealed });
    }
    prevRef.current = snapshot;
  }, [snapshot]);

  const targetableFoe = new Set<number>();
  if (mode.kind === "play") {
    for (const s of mode.card.legal_targets) targetableFoe.add(s);
  } else if (mode.kind === "attack") {
    for (const t of mode.card.attack_targets ?? []) {
      if (t.kind === "broadcast" && t.serial != null) targetableFoe.add(t.serial);
    }
  }
  const targetableFace =
    mode.kind === "attack" &&
    (mode.card.attack_targets ?? []).some((t) => t.kind === "face");
  const selectedSerial = mode.kind === "attack" ? mode.card.serial : null;
  const activeHandSerial = mode.kind === "play" ? mode.card.serial : null;

  return (
    <div className="duel-screen">
      <History history={snapshot.history} />
      <div className="duel-board">
        <PlayerZone
          title="RIVAL STATION"
          player={snapshot.foe}
          targetableFace={targetableFace}
          onClick={targetableFace ? props.onClickFace : undefined}
        />
        <BoardRow
          player={snapshot.foe}
          targetable={targetableFoe}
          onCardClick={(c) => props.onClickFoe(c)}
          fx={fx}
        />
        <div className="broadcast-line" role="status">
          <span>{status}</span>
        </div>
        <BoardRow
          player={snapshot.me}
          targetable={new Set()}
          selectedSerial={selectedSerial}
          onCardClick={(c) => props.onClickMine(c)}
          fx={fx}
        />
        <PlayerZone
          title="YOUR STATION"
          player={snapshot.me}
          mine
          canEndTurn={snapshot.can_act}
          onEndTurn={props.onEndTurn}
        />
        <Hand
          hand={snapshot.hand}
          activeSerial={activeHandSerial}
          onCardClick={(c) => props.onPlayCard(c)}
        />
      </div>
      {snapshot.winner !== null && (
        <EndGameOverlay snapshot={snapshot} onRestart={props.onRestart} />
      )}
    </div>
  );
}
