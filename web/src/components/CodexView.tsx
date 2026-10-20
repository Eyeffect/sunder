import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { planeMeta } from "../planes";
import type { SleeveDef } from "../sleeves";
import { setSleeves } from "../sleeves";
import { sleeveFromDef } from "../sleeves";
import { CardBack } from "./CardBack";
import type {
  CodexCard,
  GeneratedPack,
  Keyword,
  RegistryData,
  RegistryEntry,
  Tag,
} from "../types";
import { CostBars } from "./Card";

type Tab = "cards" | "keywords" | "generate" | "sleeves";

const TYPE_OPTS = ["BROADCAST", "TRACK", "LOOP"];

function CardTile({
  c,
  keywordByKey,
  tagByKey,
  kwActive,
  onKw,
}: {
  c: CodexCard;
  keywordByKey: Map<string, Keyword>;
  tagByKey: Map<string, Tag>;
  kwActive: string;
  onKw: (k: string) => void;
}) {
  const meta = planeMeta(c.plane);
  const style = { "--plane-color": meta.color } as CSSProperties;
  return (
    <div
      className={`card codex-card size-lg card-${c.type.toLowerCase()} rarity-${c.rarity.toLowerCase()}`}
      style={style}
    >
      <div className="card-plane-strip" />
      <div className="card-top">
        <CostBars cost={c.cost} />
        <span className="card-plane-tag">{meta.label}</span>
      </div>
      <div className="card-name">{c.name}</div>
      <div className="card-type">{c.type}</div>
      {c.keywords.length > 0 && (
        <div className="card-kw codex-kw">
          {c.keywords.map((key) => {
            const k = keywordByKey.get(key);
            return (
              <span
                key={key}
                className={`kw-chip ${kwActive === key ? "kw-chip-active" : ""}`}
                title={k?.meaning}
                onClick={(e) => {
                  e.stopPropagation();
                  onKw(key);
                }}
              >
                {k?.display ?? key}
              </span>
            );
          })}
        </div>
      )}
      {c.tags && c.tags.length > 0 && (
        <div className="card-tags">
          {c.tags.map((t) => (
            <span key={t} className="tag-chip" title={tagByKey.get(t)?.definition ?? `#${t}`}>
              {t}
            </span>
          ))}
        </div>
      )}
      {c.type === "BROADCAST" && (
        <div className="card-stats">
          <span className="stat atk">{c.atk}</span>
          <span className="stat-div">/</span>
          <span className="stat def">{c.def}</span>
        </div>
      )}
      <div className="codex-rules">{c.rules}</div>
      {c.flavor && <div className="codex-flavor">“{c.flavor}”</div>}
    </div>
  );
}

function RegistryList({
  title,
  entries,
  onApprove,
}: {
  title: string;
  entries: RegistryEntry[];
  onApprove: (id: string) => void;
}) {
  const approved = entries.filter((e) => e.status === "approved");
  const pending = entries.filter((e) => e.status !== "approved");
  return (
    <div className="registry-group">
      <div className="registry-group-title">{title}</div>
      {pending.length > 0 && (
        <div className="registry-list">
          {pending.map((e) => (
            <div key={e.id} className="registry-item pending">
              <div className="registry-id">
                {e.id}
                <span className="registry-status">{e.status}</span>
              </div>
              <div className="registry-def">
                {e.definition}
                {e.mechanic && (
                  <span className="registry-mechanic">MECHANIC</span>
                )}
              </div>
              <div className="registry-reminder">{e.reminder}</div>
              <button
                className="filter-pill registry-approve"
                onClick={() => onApprove(e.id)}
                type="button"
              >
                APPROVE
              </button>
            </div>
          ))}
        </div>
      )}
      {approved.length > 0 && (
        <div className="registry-list">
          {approved.map((e) => (
            <div key={e.id} className="registry-item approved">
              <div className="registry-id">
                {e.id}
                <span className="registry-status approved">approved</span>
              </div>
              <div className="registry-def">
                {e.definition}
                {e.mechanic && (
                  <span className="registry-mechanic">MECHANIC</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function CodexView({
  mySleeve = "ember",
  onSetSleeve,
}: {
  mySleeve?: string;
  onSetSleeve?: (id: string) => void;
}) {
  const [tab, setTab] = useState<Tab>("cards");
  const [cards, setCards] = useState<CodexCard[]>([]);
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [registry, setRegistry] = useState<RegistryData>({ tags: [], keywords: [] });
  const [query, setQuery] = useState("");
  const [plane, setPlane] = useState("all");
  const [type, setType] = useState("all");
  const [kw, setKw] = useState("all");

  const [theme, setTheme] = useState("");
  const [count, setCount] = useState(5);
  const [seed, setSeed] = useState("");
  const [generating, setGenerating] = useState(false);
  const [pack, setPack] = useState<GeneratedPack | null>(null);
  const [genError, setGenError] = useState("");

  const [proposeKind, setProposeKind] = useState<"tag" | "keyword">("tag");
  const [proposeId, setProposeId] = useState("");
  const [proposeDef, setProposeDef] = useState("");
  const [proposeReminder, setProposeReminder] = useState("");
  const [proposeMsg, setProposeMsg] = useState("");

  const refreshRegistry = () => {
    fetch("/api/registry")
      .then((r) => r.json().catch(() => ({})))
      .then((d) =>
        setRegistry({
          tags: d.tags ?? [],
          keywords: d.keywords ?? [],
        }),
      )
      .catch(() => setRegistry({ tags: [], keywords: [] }));
  };

  useEffect(() => {
    const j = (r: Response) => r.json().catch(() => ({}));
    fetch("/api/cards")
      .then(j)
      .then((d) => setCards(d.cards ?? []))
      .catch(() => setCards([]));
    fetch("/api/keywords")
      .then(j)
      .then((d) => setKeywords(d.keywords ?? []))
      .catch(() => setKeywords([]));
    fetch("/api/tags")
      .then(j)
      .then((d) => setTags(d.tags ?? []))
      .catch(() => setTags([]));
    refreshRegistry();
  }, []);

  const keywordByKey = useMemo(
    () => new Map(keywords.map((k) => [k.key, k])),
    [keywords],
  );
  const tagByKey = useMemo(() => new Map(tags.map((t) => [t.id, t])), [tags]);

  const planeOpts = useMemo(() => {
    const seen = new Set<string>();
    const opts: { value: string; label: string; color: string }[] = [];
    for (const c of cards) {
      if (seen.has(c.plane)) continue;
      seen.add(c.plane);
      const m = planeMeta(c.plane);
      opts.push({ value: c.plane, label: m.label, color: m.color });
    }
    return opts;
  }, [cards]);

  const kwOpts = useMemo(
    () => keywords.map((k) => ({ value: k.key, label: k.display })),
    [keywords],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return cards.filter((c) => {
      if (q) {
        const keys = c.keywords.join(" ").toLowerCase();
        const displays = c.keywords
          .map((k) => keywordByKey.get(k)?.display ?? "")
          .join(" ")
          .toLowerCase();
        const tagsText = (c.tags ?? []).join(" ").toLowerCase();
        if (
          ![c.name, c.id, c.type, keys, displays, tagsText]
            .join(" ")
            .toLowerCase()
            .includes(q)
        ) {
          return false;
        }
      }
      if (plane !== "all" && c.plane !== plane) return false;
      if (type !== "all" && c.type !== type) return false;
      if (kw !== "all" && !c.keywords.includes(kw)) return false;
      return true;
    });
  }, [cards, keywords, query, plane, type, kw, keywordByKey]);

  const toggleKw = (key: string) => {
    setKw((k) => (k === key ? "all" : key));
  };

  const generate = async () => {
    const t = theme.trim();
    if (!t || generating) return;
    setGenerating(true);
    setGenError("");
    setPack(null);
    try {
      const r = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          theme: t,
          count,
          seed: seed === "" ? null : Number(seed),
        }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) {
        setGenError(d.error ?? "generation failed");
      } else {
        setPack(d as GeneratedPack);
        refreshRegistry();
      }
    } catch {
      setGenError("generation failed");
    } finally {
      setGenerating(false);
    }
  };

  const propose = async () => {
    const id = proposeId.trim();
    if (!id) return;
    setProposeMsg("");
    try {
      const r = await fetch("/api/registry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind: proposeKind,
          id,
          definition: proposeDef.trim(),
          reminder: proposeReminder.trim(),
        }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) {
        setProposeMsg(d.error ?? "proposal failed");
        return;
      }
      setProposeMsg("Proposed — pending approval.");
      setProposeId("");
      setProposeDef("");
      setProposeReminder("");
      refreshRegistry();
    } catch {
      setProposeMsg("proposal failed");
    }
  };

  const approve = async (kind: "tag" | "keyword", id: string) => {
    try {
      await fetch(`/api/registry/${kind}/${id}/approve`, { method: "POST" });
      refreshRegistry();
    } catch {
      setProposeMsg("approval failed");
    }
  };

  return (
    <div className="codex-screen">
      <div className="codex-tab-bar">
        <button
          className={`codex-tab-btn ${tab === "cards" ? "active" : ""}`}
          onClick={() => setTab("cards")}
          type="button"
        >
          CARDS
        </button>
        <button
          className={`codex-tab-btn ${tab === "keywords" ? "active" : ""}`}
          onClick={() => setTab("keywords")}
          type="button"
        >
          KEYWORDS
        </button>
        <button
          className={`codex-tab-btn ${tab === "generate" ? "active" : ""}`}
          onClick={() => setTab("generate")}
          type="button"
        >
          GENERATE
        </button>
        <button
          className={`codex-tab-btn ${tab === "sleeves" ? "active" : ""}`}
          onClick={() => setTab("sleeves")}
          type="button"
        >
          SLEEVES
        </button>
      </div>

      {tab === "sleeves" && (
        <SleeveGallery active={mySleeve} onPick={onSetSleeve} />
      )}

      {tab === "cards" && (
        <section className="codex-section">
          <div className="codex-controls">
            <div className="codex-search">
              <input
                placeholder="SEARCH CARDS..."
                aria-label="Search cards"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>

            <div className="codex-filters">
              <div className="filter-row">
                <span className="filter-label">PLANE</span>
                <button
                  className={`filter-pill ${plane === "all" ? "active" : ""}`}
                  onClick={() => setPlane("all")}
                  type="button"
                >
                  ALL PLANES
                </button>
                {planeOpts.map((o) => (
                  <button
                    key={o.value}
                    className={`filter-pill ${plane === o.value ? "active" : ""}`}
                    onClick={() => setPlane(o.value)}
                    style={
                      plane === o.value
                        ? { borderColor: o.color, color: o.color, background: `${o.color}1a` }
                        : undefined
                    }
                    type="button"
                  >
                    <span className="filter-dot" style={{ background: o.color }} />
                    {o.label}
                  </button>
                ))}
              </div>

              <div className="filter-row">
                <span className="filter-label">TYPE</span>
                <button
                  className={`filter-pill ${type === "all" ? "active" : ""}`}
                  onClick={() => setType("all")}
                  type="button"
                >
                  ALL TYPES
                </button>
                {TYPE_OPTS.map((t) => (
                  <button
                    key={t}
                    className={`filter-pill ${type === t ? "active" : ""}`}
                    onClick={() => setType(t)}
                    type="button"
                  >
                    {t}
                  </button>
                ))}
              </div>

              <div className="filter-row">
                <span className="filter-label">KEYWORD</span>
                <button
                  className={`filter-pill ${kw === "all" ? "active" : ""}`}
                  onClick={() => setKw("all")}
                  type="button"
                >
                  ALL
                </button>
                {kwOpts.map((o) => (
                  <button
                    key={o.value}
                    className={`filter-pill ${kw === o.value ? "active" : ""}`}
                    onClick={() => toggleKw(o.value)}
                    type="button"
                  >
                    {o.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="codex-result-meta">
            <span className="codex-count-num">{filtered.length}</span> CARD
            {filtered.length !== 1 ? "S" : ""} FOUND
          </div>

          <div className="codex-grid">
            {filtered.length > 0 ? (
              filtered.map((c) => (
                <CardTile
                  key={c.id}
                  c={c}
                  keywordByKey={keywordByKey}
                  tagByKey={tagByKey}
                  kwActive={kw}
                  onKw={toggleKw}
                />
              ))
            ) : (
              <p className="codex-empty">NO CARDS MATCH YOUR FILTERS</p>
            )}
          </div>
        </section>
      )}

      {tab === "keywords" && (
        <section className="codex-section">
          <div className="keyword-list">
            {keywords.map((k) => (
              <div key={k.key} className="keyword-item">
                <div className="keyword-name">{k.display}</div>
                <div className="keyword-def">{k.meaning}</div>
                <div className="keyword-note">{k.kind}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {tab === "generate" && (
        <section className="codex-section gen-section">
          <div className="gen-form">
            <div className="gen-field">
              <span className="filter-label">THEME</span>
              <input
                value={theme}
                onChange={(e) => setTheme(e.target.value)}
                placeholder="e.g. jazz club"
                aria-label="Theme"
              />
            </div>
            <div className="gen-field">
              <span className="filter-label">CARDS</span>
              <input
                type="number"
                min={1}
                max={10}
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
                aria-label="Count"
              />
            </div>
            <div className="gen-field">
              <span className="filter-label">SEED</span>
              <input
                value={seed}
                onChange={(e) => setSeed(e.target.value)}
                placeholder="optional"
                aria-label="Seed"
              />
            </div>
            <button
              className="filter-pill gen-go"
              onClick={generate}
              disabled={generating || !theme.trim()}
              type="button"
            >
              {generating ? "TUNING THE SIGNAL…" : "TRANSMIT PACK"}
            </button>
          </div>

          {genError && <p className="gen-error">{genError}</p>}

          {pack && (
            <>
              <div className="gen-meta">
                {pack.theme.toUpperCase()} · SEED {pack.seed ?? "RANDOM"} · MODE{" "}
                {pack.mode.toUpperCase()}
              </div>
              <div className="codex-grid">
                {pack.cards.map((c) => (
                  <CardTile
                    key={c.id}
                    c={c}
                    keywordByKey={keywordByKey}
                    tagByKey={tagByKey}
                    kwActive=""
                    onKw={toggleKw}
                  />
                ))}
              </div>
            </>
          )}

          <div className="registry-panel">
            <div className="registry-title">TAG & KEYWORD REGISTRY</div>
            <p className="registry-note">
              Tags appear on generated cards. Custom keywords are recorded for
              later but won't appear on generated cards until mechanics land.
            </p>
            <div className="registry-propose">
              <select
                value={proposeKind}
                onChange={(e) => setProposeKind(e.target.value as "tag" | "keyword")}
                aria-label="Registry kind"
              >
                <option value="tag">tag</option>
                <option value="keyword">keyword</option>
              </select>
              <input
                value={proposeId}
                onChange={(e) => setProposeId(e.target.value)}
                placeholder="id (snake_case)"
                aria-label="Registry id"
              />
              <input
                value={proposeDef}
                onChange={(e) => setProposeDef(e.target.value)}
                placeholder="definition"
                aria-label="Definition"
              />
              <input
                value={proposeReminder}
                onChange={(e) => setProposeReminder(e.target.value)}
                placeholder="reminder text"
                aria-label="Reminder"
              />
              <button className="filter-pill" onClick={propose} type="button">
                PROPOSE
              </button>
            </div>
            {proposeMsg && <p className="gen-error">{proposeMsg}</p>}
            <RegistryList
              title="TAGS"
              entries={registry.tags}
              onApprove={(id) => approve("tag", id)}
            />
            <RegistryList
              title="KEYWORDS"
              entries={registry.keywords}
              onApprove={(id) => approve("keyword", id)}
            />
          </div>
        </section>
      )}
    </div>
  );
}

/** Card-back gallery: previews every sleeve from /api/sleeves, click to apply. */
export function SleeveGallery({
  active,
  onPick,
}: {
  active: string;
  onPick?: (id: string) => void;
}) {
  const [sleeves, setLocal] = useState<SleeveDef[]>([]);

  useEffect(() => {
    let alive = true;
    fetch("/api/sleeves")
      .then((r) => r.json())
      .then((data) => {
        if (alive && Array.isArray(data?.sleeves)) {
          setSleeves(data.sleeves);
          setLocal(data.sleeves);
        }
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  return (
    <section className="codex-section">
      <p className="sleeve-hint">
        Pick the back your playlists wear. Your station carries it into the
        duel; the rival keeps theirs.
      </p>
      <div className="sleeve-grid">
        {sleeves.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`sleeve-tile ${s.id === active ? "active" : ""}`}
            onClick={() => onPick?.(s.id)}
            aria-pressed={s.id === active}
          >
            <CardBack sleeve={sleeveFromDef(s)} />
            <span className="sleeve-tile-label">{s.label}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
