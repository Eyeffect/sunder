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
  { label: "GENERATION", status: "planned" },
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
    version: "0.3.5",
    codename: "Test Pattern",
    date: "2026-08-10",
    changes: [
      { type: "added", text: "Tags — cards can carry up to four approved tags; X_COUNT_OF_TAG_ON_BOARD scales on the count across both stations" },
      { type: "added", text: "Registry — tag/keyword governance (propose, approve, reject) with a review panel in the codex; starter tags seeded: vinyl, chrome, ghost, static, ember, tide" },
      { type: "added", text: "GENERATE tab — LLM-assisted single-pack card generation with seeded reproducibility and a deterministic no-LLM mode" },
      { type: "added", text: "CLI card generation — python -m sunder gen" },
      { type: "added", text: "Cards render their tags in the inspector, hand, codex, and generated packs" },
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
  { status: "in_progress", text: "Card sleeves" },
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
