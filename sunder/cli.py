"""SUNDER — bare CLI battle loop (P1). You are Station 1; a heuristic AI is Station 2.

Commands:
  p <n> [face|b<k>]   play hand card n (target for Tracks that need one)
  a <n> face|b<k>     attack with board card n
  h / b / l           show hand / board / log
  e                   end turn
  q                   quit
"""

from __future__ import annotations

from . import ai as ai_mod
from .game import GameState
from .primitives import CardType, Effect, Target
from .schema import Card


def render_card(gs, inst, index=None) -> str:
    tag = ""
    if inst.card.type is CardType.BROADCAST:
        tag = f" {gs.effective_atk(inst)}/{gs.def_remaining(inst)}"
    kw = f" [{', '.join(inst.card.keywords)}]" if inst.card.keywords else ""
    fuse = f" ⏲{inst.fuse_ticks}/{inst.card.fuse}" if inst.card.fuse else ""
    idx = f"{index}: " if index is not None else ""
    return f"{idx}{inst.card.name}{tag} ({inst.card.cost} BW){kw}{fuse}"


def render(gs: GameState) -> None:
    p, foe = gs.cur, gs.opp
    print()
    print(f"── OPPONENT · Signal {foe.signal} · BW {foe.bandwidth} ──")
    for i, inst in enumerate(foe.board):
        print(f"   {render_card(gs, inst, i + 1)}")
    print(f"── YOU · Signal {p.signal} · BW {p.bandwidth}/{p.max_bandwidth} ──")
    for i, inst in enumerate(p.board):
        print(f"   {render_card(gs, inst, i + 1)}")
    if p.hand:
        print("   HAND:")
        for i, inst in enumerate(p.hand):
            print(f"   [{i + 1}] {inst.card.name} ({inst.card.cost} BW) {inst.card.type.value.lower()}")
    print(f"   Turn {gs.turn} — Station {gs.current + 1}")


def _needs_target(inst) -> bool:
    return any(ab.target in (Target.CHOSEN, Target.ENEMY_BROADCAST) for ab in inst.card.abilities)


def _pick_target(gs: GameState, inst, arg: str | None) -> tuple | None:
    """Returns ('FACE', None) or ('BROADCAST', inst) for the given arg."""
    foe = gs.opp
    if arg == "face":
        return ("FACE", None)
    if arg and arg.startswith("b"):
        k = int(arg[1:]) - 1
        if 0 <= k < len(foe.board):
            return ("BROADCAST", foe.board[k])
    print("   target options: face or b<k>")
    return None


def _player_command(gs: GameState) -> bool:
    """Handle one command. Returns True to end the turn."""
    try:
        line = input("> ").strip()
    except EOFError:
        print("bye")
        raise SystemExit
    parts = line.split()
    if not parts:
        return False
    cmd = parts[0]

    if cmd in ("h", "b", "l"):
        if cmd == "l":
            for line_ in gs.log[-20:]:
                print("   " + line_)
        else:
            render(gs)
        return False

    if cmd == "e":
        return True

    if cmd == "q":
        print("quit")
        raise SystemExit

    if cmd == "p" and len(parts) >= 2:
        idx = int(parts[1]) - 1
        inst = gs.cur.hand[idx]
        chosen = None
        if _needs_target(inst):
            target = _pick_target(gs, inst, parts[2] if len(parts) > 2 else None)
            if target is None:
                return False
            chosen = target[1] if target[0] == "BROADCAST" else None
        try:
            gs.play_card(idx, chosen)
        except ValueError as exc:
            print(f"   ✗ {exc}")
        return False

    if cmd == "a" and len(parts) >= 3:
        idx = int(parts[1]) - 1
        attacker = gs.cur.board[idx]
        target = _pick_target(gs, attacker, parts[2])
        if target is None:
            return False
        try:
            gs.attack(attacker, target)
        except ValueError as exc:
            print(f"   ✗ {exc}")
        return False

    print("   commands: p <n> [target] · a <n> target · h · b · l · e · q")
    return False


def play_cli(deck1: list[Card], deck2: list[Card], seed: int | None = None) -> int:
    gs = GameState(deck1, deck2, seed=seed)
    gs.start_game()
    print("=" * 46)
    print("   SUNDER — cut the rival station off the air.")
    print("=" * 46)
    while gs.winner is None:
        if gs.current == 0:
            render(gs)
            if _player_command(gs):
                gs.end_turn()
        else:
            ai_mod.play_turn(gs)
    render(gs)
    print(f"\n  {gs.status()}")
    return gs.winner


def main() -> None:
    from pathlib import Path
    from .schema import load_card_file

    here = Path(__file__).parent
    deck1 = load_card_file(here / "cards" / "neon_frequency.json")
    deck2 = load_card_file(here / "cards" / "cinderworks.json")
    play_cli(deck1, deck2)


if __name__ == "__main__":
    main()
