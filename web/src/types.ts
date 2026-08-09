export type CardType = "BROADCAST" | "TRACK" | "LOOP";
export type Rarity = "COMMON" | "UNCOMMON" | "RARE" | "SUNDERED";

export interface AttackTarget {
  kind: "face" | "broadcast";
  serial?: number;
}

export interface BoardCard {
  serial: number;
  hidden: boolean;
  type: CardType | null;
  name: string;
  keywords: string[];
  is_token: boolean;
  cost?: number;
  plane?: string;
  atk?: number;
  def?: number;
  damage?: number;
  fuse?: number | null;
  fuse_ticks?: number;
  can_attack?: boolean;
  attack_targets?: AttackTarget[];
  rules?: string;
  flavor?: string;
}

export interface HandCard {
  serial: number;
  id: string;
  name: string;
  cost: number;
  plane?: string;
  type: CardType;
  keywords: string[];
  atk: number;
  def: number;
  rules: string;
  flavor: string;
  is_playable: boolean;
  needs_target: boolean;
  legal_targets: number[];
}

export interface PlayerState {
  index: number;
  sleeve: string;
  signal: number;
  bandwidth: number;
  max_bandwidth: number;
  hand_count: number;
  static_count: number;
  playlist_count: number;
  board: BoardCard[];
}

export interface HistoryCard {
  serial: number;
  name: string;
  type: CardType | null;
  plane: string;
  cost?: number | null;
  keywords: string[];
  is_token: boolean;
  station: number;
}

export interface HistoryEvent {
  kind:
    | "play"
    | "attack"
    | "face_attack"
    | "damage"
    | "death"
    | "reveal"
    | "draw"
    | "summon"
    | "win"
    | "system";
  text: string;
  station?: number;
  card?: HistoryCard;
}

export interface Snapshot {
  turn: number;
  current: number;
  phase: string;
  winner: number | null;
  status: string;
  viewer: number;
  can_act: boolean;
  players: Record<number, PlayerState>;
  me: PlayerState;
  foe: PlayerState;
  hand: HandCard[];
  log: string[];
  log_offset: number;
  history: HistoryEvent[];
}

export type Mode =
  | { kind: "none" }
  | { kind: "play"; card: HandCard }
  | { kind: "attack"; card: BoardCard };

export interface CodexCard {
  id: string;
  name: string;
  set: string;
  plane: string;
  rarity: Rarity;
  cost: number;
  type: CardType;
  atk: number;
  def: number;
  keywords: string[];
  rules: string;
  flavor: string;
}

export interface Keyword {
  key: string;
  display: string;
  meaning: string;
  kind: string;
}

export interface ServerMsg {
  type: "state" | "error" | "pong";
  snapshot?: Snapshot;
  message?: string;
}

export type ClientMsg =
  | { type: "start"; seed?: number }
  | { type: "restart"; seed?: number }
  | { type: "play"; hand: number; target?: number | null }
  | { type: "attack"; board: number; target: "face" | number }
  | { type: "end_turn"; turn: number }
  | { type: "ping" };
