from pathlib import Path

from sunder import ai
from sunder.game import GameState
from sunder.schema import load_card_file

CARDS = Path(__file__).parent.parent / "sunder" / "cards"


def run_match(seed, max_turns=400):
    deck1 = load_card_file(CARDS / "neon_frequency.json")
    deck2 = load_card_file(CARDS / "cinderworks.json")
    gs = GameState(deck1, deck2, seed=seed)
    gs.start_game()
    turns = 0
    while gs.winner is None and turns < max_turns:
        ai.play_turn(gs)
        turns += 1
    return gs


def test_match_completes():
    gs = run_match(seed=1)
    assert gs.winner is not None


def test_matches_complete_across_seeds():
    for seed in range(1, 8):
        gs = run_match(seed=seed)
        assert gs.winner is not None, f"seed {seed} did not finish"


def test_match_is_deterministic():
    a = run_match(seed=42)
    b = run_match(seed=42)
    assert a.winner == b.winner
    assert a.turn == b.turn
    assert a.log == b.log
