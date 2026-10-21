"""SUNDER — game state machine: zones, turn loop, combat, win/loss.

`game` owns state; `engine` owns effect resolution. No I/O here.
"""

from __future__ import annotations

import random

from . import engine
from .avatars import load_avatars
from .primitives import CardType, Effect, Scaling, Target, Trigger
from .schema import Card
from .sleeves import load_manifest, seat_sleeve

MAX_SIGNAL = 30
MAX_BANDWIDTH = 10
BOARD_CAP = 6


class CardInstance:
    """A card in play (zone-aware). `def`-style stat is stored as base +
    permanent buff; damage is tracked separately so buffs read naturally.
    """

    __slots__ = (
        "card", "serial", "controller", "zone", "is_token",
        "base_atk", "base_def", "buff_atk", "buff_def", "damage_taken",
        "aired_this_turn", "attacked_this_turn",
        "filter_spent", "mask_broken", "fuse_ticks",
        "pending_doubles", "trigger_counts", "granted_keywords", "hidden",
    )

    def __init__(self, card: Card, serial: int, controller: int):
        self.card = card
        self.serial = serial
        self.controller = controller
        self.zone = "PLAYLIST"
        self.is_token = False
        self.base_atk = card.atk
        self.base_def = card.def_
        self.buff_atk = 0
        self.buff_def = 0
        self.damage_taken = 0
        self.aired_this_turn = False
        self.attacked_this_turn = 0
        self.filter_spent = False
        self.mask_broken = False
        self.fuse_ticks = 0
        self.pending_doubles = 0
        self.trigger_counts = {}
        self.granted_keywords = set()
        self.hidden = False

    def has(self, key: str) -> bool:
        return key in self.card.keywords or key in self.granted_keywords

    def label(self) -> str:
        return self.card.name


class Player:
    def __init__(self, index: int, deck_cards: list[Card], gs: "GameState"):
        self.index = index
        self.gs = gs
        self.sleeve = seat_sleeve(gs.sleeves, deck_cards, index)
        self.avatar = next(iter(gs.avatars), "frequency")
        self.signal = MAX_SIGNAL
        self.bandwidth = 0
        self.max_bandwidth = 1
        self.turns_taken = 0
        self.bandwidth_bonus = 0
        self.uncapped = False
        self.playlist: list[CardInstance] = []
        self.hand: list[CardInstance] = []
        self.board: list[CardInstance] = []
        self.static: list[CardInstance] = []
        self.cards_played_this_turn = 0

        for c in deck_cards:
            inst = gs.make_instance(c, index)
            inst.zone = "PLAYLIST"
            self.playlist.append(inst)

    @property
    def opponent(self) -> "Player":
        return self.gs.players[1 - self.index]

    def current_max_bandwidth(self) -> int:
        base = self.turns_taken + self.bandwidth_bonus
        if self.uncapped:
            return base
        return min(MAX_BANDWIDTH, base)


class GameState:
    def __init__(self, deck1: list[Card], deck2: list[Card],
                 seed: int | None = None,
                 sleeves: dict[str, dict] | None = None,
                 avatars: dict[str, dict] | None = None):
        self.rng = random.Random(seed)
        self.turn = 1
        self.current = 0
        self.phase = "SETUP"
        self.log: list[str] = []
        self.history: list[dict] = []
        self.serial = 0
        self.lethal_hits: set[int] = set()
        self.resolving: set[int] = set()
        self.last_track_stack: list[CardInstance] = []
        self.winner: int | None = None
        self.sleeves = sleeves if sleeves is not None else load_manifest()
        self.avatars = avatars if avatars is not None else load_avatars()
        self.players = [Player(0, deck1, self), Player(1, deck2, self)]

    # ------------------------------------------------------------------ setup

    @property
    def game_over(self) -> bool:
        """True once a station has won. Use this, never `if self.winner:` —
        station 0 winning is `winner == 0`, which is falsy."""
        return self.winner is not None

    def make_instance(self, card: Card, controller: int) -> CardInstance:
        self.serial += 1
        return CardInstance(card, self.serial, controller)

    @property
    def cur(self) -> Player:
        return self.players[self.current]

    @property
    def opp(self) -> Player:
        return self.players[1 - self.current]

    def _mini_card(self, inst, station: int | None = None) -> dict:
        if inst.hidden:
            return {
                "serial": inst.serial,
                "name": "???",
                "type": None,
                "plane": "",
                "cost": None,
                "keywords": ["B_SIDE"],
                "is_token": inst.is_token,
                "station": inst.controller if station is None else station,
            }
        return {
            "serial": inst.serial,
            "name": inst.card.name,
            "type": inst.card.type.value,
            "plane": inst.card.plane,
            "cost": inst.card.cost,
            "keywords": list(inst.card.keywords),
            "tags": list(inst.card.tags),
            "is_token": inst.is_token,
            "station": inst.controller if station is None else station,
        }

    def log_line(self, msg: str, kind: str = "system", card=None, station: int | None = None, to_history: bool = True) -> None:
        self.log.append(msg)
        if not to_history:
            return
        event: dict = {"kind": kind, "text": msg}
        if station is not None:
            event["station"] = station
        if card is not None:
            event["card"] = self._mini_card(card, station)
        self.history.append(event)

    def start_game(self, opening: int = 4) -> None:
        for p in self.players:
            self.rng.shuffle(p.playlist)
        for p in self.players:
            self.draw(p, opening, silent=True)
        # second-station compensation: going second, they draw an extra
        # card also in other games — here, a free +1-Bandwidth Track.
        inst = self.make_instance(engine.coin_card(), 1)
        inst.zone = "HAND"
        self.players[1].hand.append(inst)
        self.log_line(
            "Station 2 starts with a Signal Spike (+1 Bandwidth this turn).",
            kind="system",
            station=1,
        )
        self.current = 0
        self.begin_turn()

    # ------------------------------------------------------------------ turn

    def begin_turn(self) -> None:
        p = self.cur
        p.turns_taken += 1
        p.max_bandwidth = p.current_max_bandwidth()
        p.bandwidth = p.max_bandwidth
        p.cards_played_this_turn = 0
        for inst in p.board:
            inst.aired_this_turn = False
            inst.attacked_this_turn = 0
        self.draw(p, 1, silent=True)
        engine.begin_turn(self)
        self.phase = "MAIN"
        self.log_line(
            f"--- Turn {self.turn} — Station {p.index + 1} ---",
            kind="turn",
            station=p.index,
            to_history=False,
        )

    def end_turn(self) -> None:
        """Resolve end-of-turn effects, switch stations, and begin the next turn.

        Do nothing if a winner has already been recorded.
        """
        if self.game_over:
            return
        engine.end_turn(self)
        self.current = 1 - self.current
        self.turn += 1
        self.begin_turn()

    def draw(self, player: Player, n: int = 1, silent: bool = False) -> int:
        drawn = 0
        for _ in range(n):
            if player.playlist:
                inst = player.playlist.pop(0)
                inst.zone = "HAND"
                player.hand.append(inst)
                drawn += 1
        if drawn and not silent:
            self.log_line(
                f"Station {player.index + 1} draws {drawn}.",
                kind="draw",
                station=player.index,
            )
        return drawn

    # ------------------------------------------------------------------ play

    def play_card(self, hand_index: int, chosen: CardInstance | None = None) -> CardInstance:
        """Spend bandwidth to play the current station's card and return its instance.

        `hand_index` is zero-based. `chosen` is passed to targeting abilities;
        its legality is not checked here. Resolve effects and check for a winner.
        Raise ValueError if the game is over, the index is out of range, bandwidth
        is insufficient, or a non-Track would exceed the board cap.
        """
        if self.game_over:
            raise ValueError("game over")
        p = self.cur
        if not (0 <= hand_index < len(p.hand)):
            raise ValueError("no such card in hand")
        inst = p.hand[hand_index]
        if inst.card.cost > p.bandwidth:
            raise ValueError("not enough bandwidth")
        if inst.card.type is not CardType.TRACK and len(p.board) >= BOARD_CAP:
            raise ValueError("airwaves full")

        p.bandwidth -= inst.card.cost
        p.hand.pop(hand_index)
        p.cards_played_this_turn += 1

        if inst.card.type is CardType.TRACK:
            self.log_line(
                f"Station {p.index + 1} plays {inst.label()}.",
                kind="play",
                card=inst,
                station=p.index,
            )
            engine.play_track(self, inst, chosen)
        else:
            inst.aired_this_turn = True
            inst.zone = "AIRWAVES"
            p.board.append(inst)
            if "B_SIDE" in inst.card.keywords:
                inst.hidden = True
            name = "a secret B-SIDE" if inst.hidden else inst.label()
            self.log_line(
                f"Station {p.index + 1} plays {name}.",
                kind="play",
                card=inst,
                station=p.index,
            )
            engine.on_broadcast_played(self, inst, chosen)
        self.check_win()
        return inst

    # ------------------------------------------------------------------ combat

    def def_remaining(self, inst: CardInstance) -> int:
        return inst.base_def + inst.buff_def + self._aura(inst)[1] - inst.damage_taken

    def effective_atk(self, inst: CardInstance) -> int:
        return inst.base_atk + inst.buff_atk + self._aura(inst)[0]

    def legal_track_targets(self, inst: CardInstance) -> list:
        """Legal `chosen` targets for a Track's targeting abilities."""
        targets: list = []
        for ab in inst.card.abilities:
            if ab.target is Target.ENEMY_BROADCAST or (
                    ab.target is Target.CHOSEN
                    and ab.effect in (Effect.DEAL_DAMAGE, Effect.DESTROY)):
                targets += [i for i in self.opp.board
                            if i.card.type is CardType.BROADCAST
                            and not i.hidden and self.def_remaining(i) > 0]
            elif ab.target is Target.CHOSEN:
                targets += [i for i in self.cur.board if i.card.type is CardType.BROADCAST]
        seen, out = set(), []
        for t in targets:
            if t.serial not in seen:
                seen.add(t.serial)
                out.append(t)
        return out

    def is_playable(self, inst: CardInstance) -> bool:
        """Check hand membership, cost, board space, and Track target availability.

        Return False after game over; this does not validate a chosen target.
        """
        if self.game_over or inst not in self.cur.hand:
            return False
        if inst.card.cost > self.cur.bandwidth:
            return False
        if inst.card.type is not CardType.TRACK and len(self.cur.board) >= BOARD_CAP:
            return False
        if inst.card.type is CardType.TRACK:
            for ab in inst.card.abilities:
                if ab.target in (Target.CHOSEN, Target.ENEMY_BROADCAST):
                    if not self.legal_track_targets(inst):
                        return False
        return True

    def _aura(self, inst: CardInstance) -> tuple[int, int]:
        """CARRIER auras: STATIC BUFF_STAT to ALL_YOUR_BROADCASTS."""
        if inst.card.type is not CardType.BROADCAST:
            return (0, 0)
        atk = def_ = 0
        owner = self.players[inst.controller]
        for loop in owner.board:
            if loop.card.type is not CardType.LOOP:
                continue
            for ab in loop.card.abilities:
                if (ab.trigger is Trigger.STATIC and ab.effect is Effect.BUFF_STAT
                        and ab.target is Target.ALL_YOUR_BROADCASTS):
                    if ab.scaling is Scaling.FLAT:
                        atk += ab.value
                        def_ += ab.value_def
        return (atk, def_)

    def can_attack(self, attacker: CardInstance) -> bool:
        """Check whether a live Broadcast on the current station's board may attack.

        Honor LOUD, RUSH, and FEEDBACK limits; return False after game over.
        Target restrictions are checked separately by `legal_attack_targets`.
        """
        if self.game_over or attacker.controller != self.current:
            return False
        if attacker.card.type is not CardType.BROADCAST:
            return False
        if attacker not in self.cur.board:
            return False
        if self.def_remaining(attacker) <= 0:
            return False
        max_attacks = 2 if attacker.has("FEEDBACK") else 1
        if attacker.attacked_this_turn >= max_attacks:
            return False
        if attacker.aired_this_turn and not (attacker.has("LOUD") or attacker.has("RUSH")):
            return False
        return True

    def legal_attack_targets(self, attacker: CardInstance) -> list:
        """Returns list of ('FACE', None) or ('BROADCAST', inst)."""
        targets: list = []
        if not self.can_attack(attacker):
            return targets
        foe = self.opp
        live = [i for i in foe.board if i.card.type is CardType.BROADCAST and self.def_remaining(i) > 0]
        targetable = [i for i in live if (not i.has("MASKED") or i.mask_broken) and not i.hidden]
        beacons = [i for i in targetable if i.has("BEACON")]

        can_face = True
        if attacker.aired_this_turn and attacker.has("RUSH") and not attacker.has("LOUD"):
            can_face = False
        if beacons:
            can_face = False

        if beacons:
            targets = [("BROADCAST", i) for i in beacons]
        else:
            targets = [("BROADCAST", i) for i in targetable]
            if can_face:
                targets.append(("FACE", None))
        return targets

    def attack(self, attacker: CardInstance, target: tuple) -> None:
        """Resolve an attack, consume an attack allowance, and check for a winner.

        `target` is ('FACE', None) or ('BROADCAST', instance). Do nothing if
        the game is over or the attacker cannot attack. Otherwise, raise
        ValueError for a target outside `legal_attack_targets`.
        """
        if self.game_over or attacker.controller != self.current:
            return
        if not self.can_attack(attacker):
            return
        legal = self.legal_attack_targets(attacker)
        if target not in legal:
            raise ValueError("illegal attack target")
        engine.on_attack(self, attacker)
        if target[0] == "FACE":
            dmg = self.effective_atk(attacker)
            self.opp.signal -= dmg
            engine.drain_heal(self, attacker, dmg)
            self.log_line(
                f"Station {attacker.controller + 1}: {attacker.label()} hits the rival for {dmg}.",
                kind="face_attack",
                card=attacker,
                station=attacker.controller,
            )
        else:
            defender = target[1]
            engine.attack_trade(self, attacker, defender)
        attacker.mask_broken = True
        attacker.attacked_this_turn += 1
        self.check_win()

    # ------------------------------------------------------------------ end

    def check_win(self) -> None:
        """Record a winner when either station's Signal is at or below zero.

        Station 0 wins if both qualify. Preserve an existing winner, recording
        the win event only when a winner is first assigned.
        """
        if self.game_over:
            return
        if self.players[1].signal <= 0:
            self.winner = 0
        elif self.players[0].signal <= 0:
            self.winner = 1
        if self.winner is not None:
            self.log_line(
                f"Station {self.winner + 1} cuts the rival off the air.",
                kind="win",
                station=self.winner,
            )

    def status(self) -> str:
        return (f"Turn {self.turn} | Station {self.cur.index + 1} | "
                f"Signal {self.players[0].signal}/{MAX_SIGNAL} vs {self.players[1].signal}/{MAX_SIGNAL} | "
                f"Winner: {self.winner}")
