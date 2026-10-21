import { useCallback, useEffect, useRef, useState } from "react";
import { version } from "../package.json";
import { BackgroundShader } from "./components/BackgroundShader";
import { ChangelogView } from "./components/ChangelogView";
import { CodexView } from "./components/CodexView";
import { GameView } from "./components/GameView";
import { LobbyView } from "./components/LobbyView";
import { MatchBar } from "./components/MatchBar";
import {
  clearPvp,
  clearRoomFromUrl,
  endReasonText,
  loadPvp,
  roomFromUrl,
  savePvp,
} from "./pvp";
import type { BoardCard, ClientMsg, HandCard, MatchMeta, Mode, RoomInfo, Snapshot } from "./types";
import { SLEEVE_KEY } from "./sleeves";
import { AVATAR_KEY } from "./avatars";
import { GameSocket } from "./ws";

export default function App() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [mode, setMode] = useState<Mode>({ kind: "none" });
  const [notice, setNotice] = useState("");
  const [view, setView] = useState<"battle" | "versus" | "codex" | "changelog">("battle");
  const [match, setMatch] = useState<MatchMeta | null>(null);
  const [room, setRoom] = useState<RoomInfo | null>(null);
  const [deadline, setDeadline] = useState<number | null>(null);
  const socketRef = useRef<GameSocket | null>(null);
  // True until the first snapshot after (re)connect: a failed resume/join
  // during boot falls back to a practice match instead of a dead screen.
  const bootingRef = useRef(true);
  const roomRef = useRef<RoomInfo | null>(null);

  useEffect(() => {
    const hidden = view === "codex" || view === "changelog" || view === "versus";
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
    const sendCosmetics = () => {
      const saved = localStorage.getItem(SLEEVE_KEY);
      if (saved) sock.send({ type: "set_sleeve", sleeve: saved });
      const savedAvatar = localStorage.getItem(AVATAR_KEY);
      if (savedAvatar) sock.send({ type: "set_avatar", avatar: savedAvatar });
    };
    sock.onState = (s, m) => {
      const first = bootingRef.current;
      bootingRef.current = false;
      setSnapshot(s);
      setMatch(m ?? null);
      setDeadline(
        m?.turn_remaining != null ? Date.now() + m.turn_remaining * 1000 : null,
      );
      if (m?.mode !== "pvp") {
        roomRef.current = null;
        setRoom(null);
      }
      if (m?.mode === "pvp" && s.winner !== null) clearPvp(); // nothing left to resume
      setMode({ kind: "none" });
      setNotice("");
      if (first) sendCosmetics();
    };
    sock.onError = (m) => {
      if (bootingRef.current) {
        // resume/join from a stale link or token: fall back to practice
        clearPvp();
        clearRoomFromUrl();
        sock.send({ type: "start" });
      }
      setNotice(m);
    };
    sock.onRoom = (r) => {
      roomRef.current = r;
      setRoom(r);
      if (r.token) savePvp({ code: r.code, token: r.token });
      if (r.status === "waiting") {
        // The server closed our practice match; don't leave a dead board up.
        bootingRef.current = false;
        setSnapshot(null);
        setMatch(null);
      }
      if (r.status === "live") {
        clearRoomFromUrl();
        setView("battle");
      }
    };
    sock.onRoomClosed = (reason) => {
      const wasWaiting = roomRef.current?.status === "waiting";
      roomRef.current = null;
      setRoom(null);
      clearPvp();
      if (wasWaiting) sock.send({ type: "start" }); // cancelled hosting → practice
      if (reason === "resumed elsewhere") {
        setMatch(null);
        setSnapshot(null);
        setNotice("This match was opened in another tab.");
        sock.send({ type: "start" });
      }
    };
    sock.onOpen = () => {
      bootingRef.current = true;
      const saved = loadPvp();
      const invite = roomFromUrl();
      if (saved) sock.send({ type: "resume", code: saved.code, token: saved.token });
      else if (invite) sock.send({ type: "join_room", code: invite });
      else sock.send({ type: "start" });
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

  const setAvatar = useCallback((id: string) => {
    try {
      localStorage.setItem(AVATAR_KEY, id);
    } catch { /* storage unavailable */ }
    send({ type: "set_avatar", avatar: id });
  }, [send]);

  let savedSleeve: string | null = null;
  try {
    savedSleeve = localStorage.getItem(SLEEVE_KEY);
  } catch { /* storage unavailable */ }

  const mySleeve = snapshot?.me?.sleeve ?? savedSleeve ?? "ember";
  const inPvp = match?.mode === "pvp";
  const won = snapshot !== null && snapshot.winner === snapshot.viewer;

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
            className={`tab-btn ${view === "versus" ? "active" : ""}`}
            onClick={() => setView("versus")}
            type="button"
          >
            VERSUS
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
        {view === "versus" ? (
          <LobbyView
            room={room}
            inPvp={inPvp && snapshot?.winner === null}
            onCreate={() => send({ type: "create_room" })}
            onJoin={(code) => send({ type: "join_room", code })}
            onCancel={() => send({ type: "leave_room" })}
            onBack={() => setView("battle")}
          />
        ) : !snapshot ? (
          <div className="boot">{notice || "Connecting to the airwaves…"}</div>
        ) : view === "codex" ? (
          <CodexView
            mySleeve={mySleeve}
            onSetSleeve={setSleeve}
          />
        ) : view === "changelog" ? (
          <ChangelogView />
        ) : (
          <>
          {inPvp && match && (
            <MatchBar
              match={match}
              deadline={deadline}
              myTurn={snapshot.can_act}
              gameOver={snapshot.winner !== null}
              onConcede={() => send({ type: "concede" })}
            />
          )}
          <GameView
            snapshot={snapshot}
            mode={mode}
            status={status}
            onPlayCard={playCard}
            onClickMine={onClickMine}
            onClickFoe={onClickFoe}
            onClickFace={onClickFace}
            onEndTurn={requestEndTurn}
            onRestart={() => {
              clearPvp();
              send({ type: "restart" });
            }}
            endNote={inPvp ? endReasonText(snapshot.end_reason, won) : ""}
            restartLabel={inPvp ? "Practice vs the bot" : "Play again"}
            onSetAvatar={setAvatar}
          />
          </>
        )}
      </main>
      </div>
    </>
  );
}
