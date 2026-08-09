from sunder import engine
from sunder.primitives import Trigger

from .conftest import card, make_gs, put_board, put_hand, put_static


def play(gs, idx=0, chosen=None):
    return gs.play_card(idx, chosen)


# ---------------------------------------------------------------- damage

def test_track_deals_damage_to_chosen_broadcast():
    gs = make_gs()
    target = card(type="BROADCAST", stats={"atk": 1, "def": 5})
    disco = card(type="TRACK", abilities=[
        {"trigger": "ON_PLAY", "effect": "DEAL_DAMAGE", "target": "CHOSEN", "value": 3}])
    put_board(gs, 1, target)
    put_hand(gs, 0, disco)
    gs.cur.bandwidth = 5
    play(gs, chosen=gs.players[1].board[0])
    assert gs.players[1].board[0].damage_taken == 3


def test_track_deals_to_all_enemy_broadcasts():
    gs = make_gs()
    put_board(gs, 1, card(type="BROADCAST", stats={"atk": 1, "def": 3}), 2)
    molten = card(type="TRACK", abilities=[
        {"trigger": "ON_PLAY", "effect": "DEAL_DAMAGE", "target": "ALL_ENEMY_BROADCASTS", "value": 2}])
    put_hand(gs, 0, molten)
    gs.cur.bandwidth = 5
    play(gs)
    assert [i.damage_taken for i in gs.players[1].board] == [2, 2]


# ---------------------------------------------------------------- keywords

def test_drain_heals_on_face_damage():
    gs = make_gs()
    harp = card(type="BROADCAST", stats={"atk": 3, "def": 4}, keywords=["DRAIN"])
    put_board(gs, 0, harp)
    inst = gs.players[0].board[0]
    gs.attack(inst, ("FACE", None))
    assert gs.players[1].signal == 17
    assert gs.players[0].signal == 23


def test_filter_negates_first_damage():
    gs = make_gs()
    cap = card(type="BROADCAST", stats={"atk": 1, "def": 4}, keywords=["FILTER"])
    atk = card(type="BROADCAST", stats={"atk": 2, "def": 5})
    put_board(gs, 1, cap)
    put_board(gs, 0, atk)
    cap_inst, atk_inst = gs.players[1].board[0], gs.players[0].board[0]
    gs.attack(atk_inst, ("BROADCAST", cap_inst))
    assert cap_inst.damage_taken == 0 and cap_inst.filter_spent
    atk_inst.attacked_this_turn = 0
    gs.attack(atk_inst, ("BROADCAST", cap_inst))
    assert cap_inst.damage_taken == 2


def test_distort_is_lethal():
    gs = make_gs()
    tower = card(type="BROADCAST", stats={"atk": 2, "def": 4}, keywords=["DISTORT"])
    victim = card(type="BROADCAST", stats={"atk": 1, "def": 4})
    put_board(gs, 0, tower)
    put_board(gs, 1, victim)
    tower_inst, victim_inst = gs.players[0].board[0], gs.players[1].board[0]
    gs.attack(tower_inst, ("BROADCAST", victim_inst))
    assert victim_inst not in gs.players[1].board


def test_echo_death_gains_life():
    gs = make_gs()
    golem = card(type="BROADCAST", stats={"atk": 3, "def": 1}, abilities=[
        {"trigger": "ON_DEATH", "effect": "GAIN_LIFE", "target": "SELF", "value": 3}])
    killer = card(type="BROADCAST", stats={"atk": 5, "def": 5})
    put_board(gs, 0, golem)
    put_board(gs, 1, killer)
    golem_inst, killer_inst = gs.players[0].board[0], gs.players[1].board[0]
    gs.current = 1
    gs.attack(killer_inst, ("BROADCAST", golem_inst))
    assert golem_inst not in gs.players[0].board
    assert gs.players[0].signal == 23


def test_echo_chamber_summons_token_on_death():
    gs = make_gs()
    chamber = card(type="BROADCAST", stats={"atk": 1, "def": 1}, abilities=[
        {"trigger": "ON_DEATH", "effect": "SUMMON_TOKEN", "target": "SELF", "value": 1}])
    killer = card(type="BROADCAST", stats={"atk": 5, "def": 5})
    put_board(gs, 0, chamber)
    put_board(gs, 1, killer)
    chamber_inst, killer_inst = gs.players[0].board[0], gs.players[1].board[0]
    gs.current = 1
    gs.attack(killer_inst, ("BROADCAST", chamber_inst))
    tokens = [i for i in gs.players[0].board if i.is_token]
    assert len(tokens) == 1
    assert tokens[0].card.name == "Echo"


# ---------------------------------------------------------------- copy

def test_encore_replays_last_track():
    gs = make_gs()
    put_board(gs, 1, card(type="BROADCAST", stats={"atk": 1, "def": 5}))
    molten = card(type="TRACK", abilities=[
        {"trigger": "ON_PLAY", "effect": "DEAL_DAMAGE", "target": "ALL_ENEMY_BROADCASTS", "value": 2}])
    encore = card(type="TRACK", abilities=[
        {"trigger": "ON_PLAY", "effect": "COPY_LAST_TRACK", "target": "SELF", "value": 1}])
    put_hand(gs, 0, molten)
    put_hand(gs, 0, encore)
    gs.cur.bandwidth = 5
    play(gs, 0)
    play(gs, 0)
    assert gs.players[1].board[0].damage_taken == 4


def test_copy_fizzles_with_no_last_track():
    gs = make_gs()
    encore = card(type="TRACK", abilities=[
        {"trigger": "ON_PLAY", "effect": "COPY_LAST_TRACK", "target": "SELF", "value": 1}])
    put_hand(gs, 0, encore)
    gs.cur.bandwidth = 5
    play(gs)
    assert gs.players[0].static[-1].card.id == encore.id


# ---------------------------------------------------------------- counter

def test_counter_track_cuts():
    gs = make_gs()
    squelcher = card(type="LOOP", abilities=[
        {"trigger": "ON_CAST_TRACK", "effect": "COUNTER_TRACK", "target": "SELF", "value": 1}])
    put_board(gs, 0, squelcher)
    disco = card(type="TRACK", abilities=[
        {"trigger": "ON_PLAY", "effect": "DEAL_DAMAGE", "target": "ENEMY_FACE", "value": 3}])
    put_hand(gs, 0, disco)
    gs.cur.bandwidth = 5
    play(gs)
    assert disco in [i.card for i in gs.players[0].static]
    assert gs.players[1].signal == 20


# ---------------------------------------------------------------- doubles

def test_double_next_trigger():
    gs = make_gs()
    dripper = card(type="LOOP", abilities=[
        {"trigger": "ON_TURN_END", "effect": "DEAL_DAMAGE", "target": "ENEMY_FACE", "value": 1}])
    boost = card(type="BROADCAST", stats={"atk": 1, "def": 1}, abilities=[
        {"trigger": "ON_PLAY", "effect": "DOUBLE_NEXT_TRIGGER", "target": "CHOSEN", "value": 1}])
    put_board(gs, 0, dripper)
    drip_inst = gs.players[0].board[0]
    put_hand(gs, 0, boost)
    gs.cur.bandwidth = 5
    play(gs, chosen=drip_inst)
    assert drip_inst.pending_doubles == 1
    engine.fire(gs, drip_inst, Trigger.ON_TURN_END)
    assert gs.players[1].signal == 18


# ---------------------------------------------------------------- fuse

def test_fuse_ticks_and_detonates():
    gs = make_gs()
    cache = card(type="BROADCAST", stats={"atk": 0, "def": 4}, fuse=3, abilities=[
        {"trigger": "ON_FUSE_EXPIRED", "effect": "DEAL_DAMAGE", "target": "ENEMY_FACE", "value": 4},
        {"trigger": "ON_FUSE_EXPIRED", "effect": "DESTROY", "target": "SELF", "value": 1}])
    put_board(gs, 0, cache)
    inst = gs.players[0].board[0]
    for _ in range(2):
        engine.begin_turn(gs)
    assert inst in gs.players[0].board and inst.fuse_ticks == 2
    engine.begin_turn(gs)
    assert inst not in gs.players[0].board
    assert gs.players[1].signal == 16


# ---------------------------------------------------------------- scalings

def test_times_triggered_scaling_adds_running_count():
    """X_TIMES_THIS_TRIGGERED_THIS_GAME substitutes the running count each
    trigger — a repeatable BUFF_STAT on it snowballs quadratically. No starter
    card uses it (Foundry went linear); the primitive stays in the vocabulary."""
    gs = make_gs()
    foundry = card(type="BROADCAST", stats={"atk": 1, "def": 1}, abilities=[
        {"trigger": "ON_ANY_BROADCAST_PLAYED", "effect": "BUFF_STAT", "target": "SELF",
         "scaling": "X_TIMES_THIS_TRIGGERED_THIS_GAME", "value": 1, "value_def": 1}])
    hound = card(type="BROADCAST", stats={"atk": 2, "def": 2})
    put_hand(gs, 0, foundry)
    put_hand(gs, 0, hound)
    gs.cur.bandwidth = 5
    play(gs, 0)  # foundry enters: +1/+1
    play(gs, 0)  # hound enters: +2/+2
    foundry_inst = gs.players[0].board[0]
    assert foundry_inst.buff_atk == 3
    assert foundry_inst.buff_def == 3


def test_foundry_card_grows_linearly():
    from sunder.codex import find
    gs = make_gs()
    foundry = find("foundry")[0]
    hound = card(type="BROADCAST", stats={"atk": 2, "def": 2})
    put_hand(gs, 0, foundry)
    put_hand(gs, 0, hound)
    gs.cur.bandwidth = 5
    play(gs, 0)  # foundry enters: +1/+1
    play(gs, 0)  # hound enters: +1/+1
    foundry_inst = gs.players[0].board[0]
    assert foundry_inst.buff_atk == 2
    assert foundry_inst.buff_def == 2


# ---------------------------------------------------------------- misc effects

def test_summon_tokens():
    gs = make_gs()
    waves = card(type="TRACK", abilities=[
        {"trigger": "ON_PLAY", "effect": "SUMMON_TOKEN", "target": "SELF", "value": 2}])
    put_hand(gs, 0, waves)
    gs.cur.bandwidth = 5
    play(gs)
    assert len(gs.players[0].board) == 2
    assert all(i.is_token for i in gs.players[0].board)


def test_return_from_discard():
    gs = make_gs()
    dead = card(type="BROADCAST", stats={"atk": 1, "def": 1})
    dead_inst = put_static(gs, 0, dead)
    rewind = card(type="TRACK", abilities=[
        {"trigger": "ON_PLAY", "effect": "RETURN_FROM_DISCARD", "target": "SELF", "value": 1}])
    put_hand(gs, 0, rewind)
    gs.cur.bandwidth = 5
    play(gs)
    assert len(gs.players[0].hand) == 1
    assert gs.players[0].hand[0] is dead_inst
    assert [i.card for i in gs.players[0].static] == [rewind]


def test_turn_start_buff_loop():
    gs = make_gs()
    rink = card(type="LOOP", abilities=[
        {"trigger": "ON_TURN_END", "effect": "BUFF_STAT", "target": "SELF", "value": 1, "value_def": 1}])
    put_board(gs, 0, rink)
    engine.end_turn(gs)
    assert rink is not None
    inst = gs.players[0].board[0]
    assert inst.buff_atk == 1 and inst.buff_def == 1
