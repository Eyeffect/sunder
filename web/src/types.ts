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
  tags?: string[];
  is_token: boolean;
  cost?: number;
  plane?: string;
  rarity?: Rarity;
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
  rarity?: Rarity;
  type: CardType;
  keywords: string[];
  tags?: string[];
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
  sleeve_ink?: string;
  avatar?: string;
  avatar_glyph?: string;
  signal: number;
  max_signal: number;
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
  tags?: string[];
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
  end_reason?: EndReason | null;
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
  tags?: string[];
  rules: string;
  flavor: string;
}

export interface Keyword {
  key: string;
  display: string;
  meaning: string;
  kind: string;
}

export interface Tag {
  id: string;
  definition: string;
  reminder: string;
}

export interface Mechanic {
  trigger: string;
  effect: string;
  target: string;
  scaling: string;
  value: number;
  value_def?: number;
  tag?: string;
  keyword?: string;
  count_type?: string;
  condition?: { has_tag: string };
}

export interface RegistryEntry extends Tag {
  status: "proposed" | "approved" | "rejected";
  mechanic?: Mechanic | null;
}

export interface RegistryData {
  tags: RegistryEntry[];
  keywords: RegistryEntry[];
}

export interface GeneratedPack {
  cards: CodexCard[];
  theme: string;
  seed: number | null;
  mode: "llm" | "deterministic";
}

export type EndReason = "signal" | "concede" | "timeout" | "disconnect";

/** Per-seat match info that rides next to every `state` snapshot. */
export interface MatchMeta {
  mode: "bot" | "pvp";
  code: string | null;
  seat: number;
  opponent_connected: boolean;
  turn_seconds: number | null;
  turn_remaining: number | null;
}

/** Lobby status for this connection (docs/multiplayer.md). */
export interface RoomInfo {
  mode: "pvp";
  code: string;
  seat: number | null;
  token: string | null;
  status: "waiting" | "live" | "over";
}

export interface ServerMsg {
  type: "state" | "error" | "pong" | "room" | "room_closed";
  snapshot?: Snapshot;
  match?: MatchMeta;
  message?: string;
  // room
  mode?: "pvp";
  code?: string;
  seat?: number | null;
  token?: string | null;
  status?: RoomInfo["status"];
  // room_closed
  reason?: string;
}

export type ClientMsg =
  | { type: "start"; seed?: number }
  | { type: "restart"; seed?: number }
  | { type: "play"; hand: number; target?: number | null }
  | { type: "attack"; board: number; target: "face" | number }
  | { type: "end_turn"; turn: number }
  | { type: "set_sleeve"; sleeve: string }
  | { type: "set_avatar"; avatar: string }
  | { type: "ping" }
  | { type: "create_room" }
  | { type: "join_room"; code: string }
  | { type: "resume"; code: string; token: string }
  | { type: "leave_room" }
  | { type: "concede" };
