"""SUNDER — closed primitive vocabulary.

The engine never branches on lore; these enums are the whole grammar.
Effects are CLOSED (determinism lives here). Triggers, scalings, and
targets grow as grammar-checked data; effects stay fixed.
"""

from enum import Enum


class CardType(str, Enum):
    BROADCAST = "BROADCAST"
    TRACK = "TRACK"
    LOOP = "LOOP"


class Rarity(str, Enum):
    COMMON = "COMMON"
    UNCOMMON = "UNCOMMON"
    RARE = "RARE"
    SUNDERED = "SUNDERED"


class Trigger(str, Enum):
    ON_PLAY = "ON_PLAY"                     # this card enters play
    ON_ATTACK = "ON_ATTACK"                 # this broadcast attacks
    ON_DEATH = "ON_DEATH"                   # this broadcast is jammed
    ON_TURN_START = "ON_TURN_START"         # controller's turn start
    ON_TURN_END = "ON_TURN_END"             # controller's turn end
    ON_CAST_TRACK = "ON_CAST_TRACK"         # any track is played (pre-resolve)
    ON_ANY_BROADCAST_PLAYED = "ON_ANY_BROADCAST_PLAYED"  # any broadcast aired
    ON_FUSE_EXPIRED = "ON_FUSE_EXPIRED"     # fuse counter reached the card's fuse
    STATIC = "STATIC"                       # always-on (aura) — not event driven


class Effect(str, Enum):
    DEAL_DAMAGE = "DEAL_DAMAGE"             # deal Noise
    GAIN_LIFE = "GAIN_LIFE"                 # boost Signal
    DRAW_CARD = "DRAW_CARD"                 # cue a card
    BUFF_STAT = "BUFF_STAT"                 # permanent +atk/+def
    SUMMON_TOKEN = "SUMMON_TOKEN"           # spawn 1/1 Echo Broadcast(s)
    RETURN_FROM_DISCARD = "RETURN_FROM_DISCARD"  # rewind a card from Static
    COPY_LAST_TRACK = "COPY_LAST_TRACK"     # replay the last Track (no cast triggers)
    COUNTER_TRACK = "COUNTER_TRACK"         # cut a track mid-cast
    DESTROY = "DESTROY"                     # jam a broadcast
    GRANT_KEYWORD = "GRANT_KEYWORD"         # grant a keyword to a broadcast
    DOUBLE_NEXT_TRIGGER = "DOUBLE_NEXT_TRIGGER"  # next trigger of target fires twice
    GAIN_BANDWIDTH = "GAIN_BANDWIDTH"       # generate Bandwidth this turn
    UNCAP_BANDWIDTH = "UNCAP_BANDWIDTH"     # remove the Bandwidth cap


class Scaling(str, Enum):
    FLAT = "FLAT"
    X_COUNT_OF_TYPE_ON_BOARD = "X_COUNT_OF_TYPE_ON_BOARD"
    X_CARDS_PLAYED_THIS_TURN = "X_CARDS_PLAYED_THIS_TURN"
    X_TURN_NUMBER = "X_TURN_NUMBER"
    X_TIMES_THIS_TRIGGERED_THIS_GAME = "X_TIMES_THIS_TRIGGERED_THIS_GAME"


class Target(str, Enum):
    SELF = "SELF"
    ENEMY_FACE = "ENEMY_FACE"
    ENEMY_BROADCAST = "ENEMY_BROADCAST"
    ALL_ENEMY_BROADCASTS = "ALL_ENEMY_BROADCASTS"
    ALL_YOUR_BROADCASTS = "ALL_YOUR_BROADCASTS"
    ALL_BROADCASTS = "ALL_BROADCASTS"
    RANDOM = "RANDOM"
    CHOSEN = "CHOSEN"
