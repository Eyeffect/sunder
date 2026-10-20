import type { LucideIcon } from "lucide-react";
import { CheckCircle2, Circle, Loader2, Minus, Plus, RefreshCw, Scale, Wrench } from "lucide-react";

export type ChangeType = "added" | "changed" | "fixed" | "removed" | "balanced";

export const CHANGE_ICONS: Record<ChangeType, LucideIcon> = {
  added: Plus,
  changed: RefreshCw,
  fixed: Wrench,
  removed: Minus,
  balanced: Scale,
};

export const CHANGE_LABEL: Record<ChangeType, string> = {
  added: "ADD",
  changed: "CHG",
  fixed: "FIX",
  removed: "DEL",
  balanced: "BAL",
};

export const CHANGE_COLOR: Record<ChangeType, string> = {
  added: "var(--cyan)",
  changed: "var(--amber)",
  fixed: "var(--magenta)",
  removed: "var(--danger)",
  balanced: "var(--amber)",
};

export interface Milestone {
  label: string;
  status: "done" | "active" | "planned";
}

export const MILESTONES: Milestone[] = [
  { label: "CONCEPT", status: "done" },
  { label: "ENGINE", status: "done" },
  { label: "WEB UI", status: "done" },
  { label: "GENERATION", status: "active" },
  { label: "COLLECTION & STREAM", status: "planned" },
];

export interface Change {
  type: ChangeType;
  text: string;
}

export interface VersionEntry {
  version: string;
  codename: string;
  date: string;
  current?: boolean;
  changes: Change[];
}

export const VERSIONS: VersionEntry[] = [
  {
    version: "0.3.7.5",
    codename: "Face Value",
    date: "2026-10-20",
    current: true,
    changes: [
      { type: "changed", text: "Card faces redrawn at true 2.5×3.5 playing-card proportions — tighter type, a 5-line rules window, and one layout across hand, board, and codex" },
      { type: "added", text: "Every face prints its edition and rarity in the top-right badge, with the station code watermarked in the corner" },
      { type: "added", text: "Hand cost bars read playability: they light in the edition's colour when the card is affordable, and stay grey when it isn't" },
      { type: "added", text: "Station profile icons: pick one of the old sleeve emblems from your avatar; the glyph takes your sleeve's ink and persists between sessions" },
      { type: "changed", text: "Unplayable hand cards keep full opacity; flavor text moves to the inspector (the codex keeps its quotes)" },
      { type: "changed", text: "Board cards step down to the compact face so six slots fit; the codex field fades blue while browsing" },
      { type: "changed", text: "Sleeve art redrawn as hand-editable SVGs — emblems are part of the art now, and the roster is trimmed to nine" },
      { type: "fixed", text: "Long rules no longer slice mid-glyph in Firefox; clamped text fades at the cut" },
    ],
  },
  {
    version: "0.3.7",
    codename: "Album Cover",
    date: "2026-10-20",
    changes: [
      { type: "added", text: "Card sleeves: every deck comes wrapped in its own die-cut back — 10 hand-drawn SVG patterns, 12 sleeves" },
      { type: "added", text: "Browse and pick your sleeve in the codex SLEEVES tab; your station wears it, your opponent sees it" },
      { type: "added", text: "Deck-bound sleeves: playlists carry their plane's livery (Neon Frequency, Cinderworks, Driftglass, Sporewake)" },
      { type: "changed", text: "Deck stacks render the real sleeve art instead of a plain outline" },
      { type: "fixed", text: "Card-back chrome squared to the shared 8px cut geometry, inner frame retired" },
    ],
  },
  {
    version: "0.3.6.1",
    codename: "Feedback",
    date: "2026-10-20",
    changes: [
      { type: "changed", text: "Under-the-hood polish build — same game, new docs, care where you can't see" },
    ],
  },
  {
    version: "0.3.6",
    codename: "Feedback",
    date: "2026-10-20",
    changes: [
      { type: "added", text: "Signal Spike — going second now opens with a free Track that grants +1 Bandwidth for the turn, closing the first-move tempo gap" },
      { type: "changed", text: "AMP finally broadcasts for real — a card with AMP grows +1/+1 every time any Broadcast is aired, on either station, itself included" },
      { type: "changed", text: "Fresh tags wait for your approval in the tag library instead of joining packs instantly — a review queue now, and a tag you rejected stays rejected until you bring it back" },
      { type: "balanced", text: "Going second is no longer strictly behind — the spike evens out the opening tempo" },
      { type: "fixed", text: "ECHO always has something to say — any card carrying ECHO must also carry a death effect, and freshly generated packs are checked for it too" },
    ],
  },
  {
    version: "0.3.5",
    codename: "Worldcast",
    date: "2026-08-10",
    changes: [
      { type: "added", text: "Tags — cards can carry up to four theme tags, and some abilities grow stronger the more matching tags are on the airwaves" },
      { type: "added", text: "The tag library — browse, propose, approve, or reject tag and keyword ideas in the codex; the starter set ships with vinyl, chrome, ghost, static, ember, and tide" },
      { type: "added", text: "Tags show on cards everywhere — in your hand, the inspector, the codex, and freshly generated packs" },
      { type: "added", text: "The GENERATE tab — type any theme and get a fresh pack of cards, reliably repeatable with a seed (or fully offline with no model)" },
      { type: "added", text: "Card generation from the command line — python -m sunder gen" },
      { type: "added", text: "The multiverse opens up — card themes can be anything at all now. You're still a broadcast station; the worlds your cards come from no longer have to be radio-themed" },
      { type: "added", text: "Tags come alive — a new tag proposed for your theme carries a real ability that works in-game, and its card text is written for you" },
      { type: "added", text: "A theme's own new tags show up right away in its packs, and far more often than tags from other worlds" },
      { type: "fixed", text: "Generating could stall and hand back the same stock cards instead of your theme — the game now waits properly for the model" },
      { type: "fixed", text: "New tags appear in the library the moment a pack finishes generating, no restart needed" },
      { type: "fixed", text: "Ability text on generated cards now always says what it affects, like #frostbite dealing Noise to the rival station" },
    ],
  },
  {
    version: "0.3.4",
    codename: "Station Bulletin",
    date: "2026-08-10",
    changes: [
      { type: "added", text: "Changelog view — milestones, version log, roadmap — opens when you click the version in the wordmark" },
      { type: "added", text: "Evenly-divided signal VU meter, tick grid tied to the max" },
      { type: "balanced", text: "Max signal raised 20 → 30" },
      { type: "changed", text: "Frosted panels on stations, inspector and transmission log — more opaque with a 1px blur" },
      { type: "changed", text: "Darker shader backdrop" },
      { type: "fixed", text: "Change and status codes align in fixed-width columns" },
      { type: "fixed", text: "Scrollbar no longer shifts the layout when it appears in the codex or changelog" },
    ],
  },
  {
    version: "0.3.3.1",
    codename: "Counter-Rotate",
    date: "2026-08-10",
    changes: [
      { type: "added", text: "Background swirl now spins clockwise on your turn, counter-clockwise on the rival's" },
    ],
  },
  {
    version: "0.3.3",
    codename: "Turn Tint",
    date: "2026-08-10",
    changes: [
      { type: "added", text: "Turn-driven background colors — amber on your turn, magenta on the rival's, with a smooth eased crossfade" },
    ],
  },
  {
    version: "0.3.2",
    codename: "Signal Pacing",
    date: "2026-08-09",
    changes: [
      { type: "added", text: "Realistic AI pacing — the rival thinks and acts with timed pauses" },
      { type: "added", text: "Summon FX for newly aired cards" },
      { type: "fixed", text: "Rapid end-turn clicks could skip turns" },
      { type: "fixed", text: "Empty-hand layout broke the tray alignment" },
    ],
  },
  {
    version: "0.3.0",
    codename: "Signal Console",
    date: "2026-08-09",
    changes: [
      { type: "added", text: "Web app (React + TypeScript + Vite over FastAPI/WebSocket) replacing the Textual TUI — mouse + keyboard over the same deterministic engine" },
      { type: "added", text: "Interactive background shader — animated WebGL2 swirl with CRT scanlines" },
      { type: "added", text: "Battle UI: stations with signal VU meters, frosted panels, deck stacks, fanned hand (keys 1-9), transmission-log tray, card inspector with rules/flavor" },
      { type: "added", text: "Web codex with live search over /api/cards; version readout in the header wordmark" },
      { type: "fixed", text: "Wordmark glitch" },
    ],
  },
  {
    version: "0.2.0",
    codename: "Mirror Signal",
    date: "2026-07-29",
    changes: [
      { type: "added", text: "B-SIDE completion — hidden cards reveal the moment a listed trigger fires, stay untargetable while masked, and die hidden (mass effects still hit)" },
      { type: "added", text: "Two starter B-SIDE loops — Midnight Request and Static Replay — plus shared validation helpers (is_playable, legal_track_targets)" },
      { type: "added", text: "Textual TUI: battle screen with dual signal/bandwidth readouts, masked ??? [B-SIDE] boards, clickable hand + target mode, codex, keybindings — later replaced by the web app in P3" },
    ],
  },
  {
    version: "0.1.0",
    codename: "First Broadcast",
    date: "2026-07-24",
    changes: [
      { type: "added", text: "Core engine: primitives, card schema with validator, and ability resolver (triggers, effects, modifiers, FUSE, COPY, tokens)" },
      { type: "added", text: "GameState: zones, turn loop, combat resolution, win/loss, and event log" },
      { type: "added", text: "20 starter cards across two planes covering 12 keywords — RUSH, LOUD, ECHO, AMP, DRAIN, BEACON, MASKED, FILTER, DISTORT, CARRIER, FEEDBACK, B-SIDE" },
      { type: "added", text: "Heuristic AI opponent, scripted AI-vs-AI match, and a print-based CLI battle loop" },
    ],
  },
];

export interface RoadmapItem {
  status: "in_progress" | "planned";
  text: string;
}

export const ROADMAP: RoadmapItem[] = [
  { status: "in_progress", text: "Responsive UI" },
  { status: "in_progress", text: "LLM card generation" },
  { status: "planned", text: "Economy, saved decks" },
  { status: "planned", text: "Profiles" },
  { status: "planned", text: "Multiplayer" },
  { status: "planned", text: "Transmissions" },
  { status: "planned", text: "Growing keyword" },
  { status: "planned", text: "Deck-builder and stream" },
  { status: "planned", text: "Gauntlet, tuning" },
  { status: "planned", text: "Advanced AI" },
];

export const MILESTONE_ICONS = { done: CheckCircle2, active: Loader2, planned: Circle };
