import { useCallback, useEffect, useRef, useState } from "react";
import { version } from "../package.json";
import { BackgroundShader } from "./components/BackgroundShader";
import { ChangelogView } from "./components/ChangelogView";
import { CodexView } from "./components/CodexView";
import { GameView } from "./components/GameView";
import type { BoardCard, ClientMsg, HandCard, Mode, Snapshot } from "./types";
import { SLEEVE_KEY } from "./sleeves";
import { GameSocket } from "./ws";

export default function App() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [mode, setMode] = useState<Mode>({ kind: "none" });
  const [notice, setNotice] = useState("");
  const [view, setView] = useState<"battle" | "codex" | "changelog">("battle");
  const socketRef = useRef<GameSocket | null>(null);

  useEffect(() => {
    const hidden = view === "codex" || view === "changelog";
    document.documentElement.classList.toggle("no-scrollbar", hidden);
    return () => {
      document.documentElement.classList.toggle("no-scrollbar", false);
    };
  }, [view]);

  const send = useCallback((msg: ClientMsg) => {
    socketRef.current?.send(msg);
  }, []);

  const requestEndTurn = useCallback(() => {
    if (!snapshot?.can_act) return;
    send({ type: "end_turn", turn: snapshot.turn });
  }, [snapshot, send]);

  useEffect(() => {
    const sock = new GameSocket();
    socketRef.current = sock;
    sock.onState = (s) => {
      setSnapshot(s);
      setMode({ kind: "none" });
      setNotice("");
    };
    sock.onError = (m) => setNotice(m);
    sock.onOpen = () => {
      sock.send({ type: "start" });
      const saved = localStorage.getItem(SLEEVE_KEY);
      if (saved) sock.send({ type: "set_sleeve", sleeve: saved });
    };
    sock.connect();
    return () => sock.close();
  }, []);

  const playCard = useCallback(
    (card: HandCard) => {
      if (!snapshot?.can_act) return;
      if (card.needs_target) {
        if (card.legal_targets.length === 0) {
          setNotice("No legal target.");
          return;
        }
        setMode({ kind: "play", card });
        return;
      }
      send({ type: "play", hand: snapshot.hand.indexOf(card) });
    },
    [snapshot, send],
  );

  const onClickMine = useCallback(
    (card: BoardCard) => {
      if (!snapshot?.can_act || mode.kind !== "none") return;
      if (!card.can_attack) return;
      if ((card.attack_targets ?? []).length === 0) {
        setNotice("Nothing to hit.");
        return;
      }
      setMode({ kind: "attack", card });
    },
    [snapshot, mode],
  );

  const onClickFoe = useCallback(
    (card: BoardCard) => {
      if (!snapshot) return;
      if (mode.kind === "play") {
        if (mode.card.legal_targets.includes(card.serial)) {
          send({ type: "play", hand: snapshot.hand.indexOf(mode.card), target: card.serial });
        }
      } else if (mode.kind === "attack") {
        if (mode.card.attack_targets?.some((t) => t.kind === "broadcast" && t.serial === card.serial)) {
          send({ type: "attack", board: snapshot.me.board.indexOf(mode.card), target: card.serial });
        }
      }
    },
    [snapshot, mode, send],
  );

  const onClickFace = useCallback(() => {
    if (!snapshot || mode.kind !== "attack") return;
    if (mode.card.attack_targets?.some((t) => t.kind === "face")) {
      send({ type: "attack", board: snapshot.me.board.indexOf(mode.card), target: "face" });
    }
  }, [snapshot, mode, send]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (view !== "battle" || !snapshot) return;
      if (e.key === "Escape") {
        setMode({ kind: "none" });
        return;
      }
      if (e.key === "e") {
        requestEndTurn();
        return;
      }
      if (e.key === "c") {
        setView("codex");
        return;
      }
      if (/^[1-9]$/.test(e.key)) {
        const card = snapshot.hand[Number(e.key) - 1];
        if (card) playCard(card);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [view, snapshot, requestEndTurn, playCard]);

  const status =
    notice ||
    (mode.kind === "play"
      ? `Choose a target for ${mode.card.name}.`
      : mode.kind === "attack"
        ? `Choose an attack target for ${mode.card.name}.`
        : snapshot?.can_act
          ? "Your turn — air a card or attack."
          : "The rival is playing…");

  const setSleeve = useCallback((id: string) => {
    try {
      localStorage.setItem(SLEEVE_KEY, id);
    } catch { /* storage unavailable */ }
    send({ type: "set_sleeve", sleeve: id });
  }, [send]);

  let savedSleeve: string | null = null;
  try {
    savedSleeve = localStorage.getItem(SLEEVE_KEY);
  } catch { /* storage unavailable */ }

  const mySleeve = snapshot?.players?.[0]?.sleeve ?? savedSleeve ?? "ember";

  return (
    <>
      <BackgroundShader
        turnSide={snapshot?.can_act ?? null}
        codex={view === "codex"}
      />
      <div className="layout">
      <header className="sunder-header">
        <div className="wordmark">
          SUNDER{" "}
          <button
            className="freq"
            onClick={() => setView("changelog")}
            title="Changelog"
            type="button"
          >
            v{version}
          </button>
        </div>
        <nav className="tabs">
          <button
            className={`tab-btn ${view === "battle" ? "active" : ""}`}
            onClick={() => setView("battle")}
            type="button"
          >
            DUEL
          </button>
          <button
            className={`tab-btn ${view === "codex" ? "active" : ""}`}
            onClick={() => setView("codex")}
            type="button"
          >
            CODEX
          </button>
        </nav>
        <div className="turn-readout">
          TURN <span>{snapshot ? String(snapshot.turn).padStart(2, "0") : "--"}</span>
        </div>
      </header>
      <main className="sunder-main">
        {!snapshot ? (
          <div className="boot">Connecting to the airwaves…</div>
        ) : view === "codex" ? (
          <CodexView
            mySleeve={mySleeve}
            onSetSleeve={setSleeve}
          />
        ) : view === "changelog" ? (
          <ChangelogView />
        ) : (
          <GameView
            snapshot={snapshot}
            mode={mode}
            status={status}
            onPlayCard={playCard}
            onClickMine={onClickMine}
            onClickFoe={onClickFoe}
            onClickFace={onClickFace}
            onEndTurn={requestEndTurn}
            onRestart={() => send({ type: "restart" })}
          />
        )}
      </main>
      </div>
    </>
  );
}
