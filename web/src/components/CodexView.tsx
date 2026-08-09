import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { planeMeta } from "../planes";
import type { CodexCard, Keyword } from "../types";
import { CostBars } from "./Card";

type Tab = "cards" | "keywords";

const TYPE_OPTS = ["BROADCAST", "TRACK", "LOOP"];

export function CodexView() {
  const [tab, setTab] = useState<Tab>("cards");
  const [cards, setCards] = useState<CodexCard[]>([]);
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [query, setQuery] = useState("");
  const [plane, setPlane] = useState("all");
  const [type, setType] = useState("all");
  const [kw, setKw] = useState("all");

  useEffect(() => {
    fetch("/api/cards")
      .then((r) => r.json())
      .then((d) => setCards(d.cards))
      .catch(() => setCards([]));
    fetch("/api/keywords")
      .then((r) => r.json())
      .then((d) => setKeywords(d.keywords))
      .catch(() => setKeywords([]));
  }, []);

  const keywordByKey = useMemo(
    () => new Map(keywords.map((k) => [k.key, k])),
    [keywords],
  );

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
        if (![c.name, c.id, c.type, keys, displays].join(" ").toLowerCase().includes(q)) {
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
      </div>

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
              filtered.map((c) => {
                const meta = planeMeta(c.plane);
                const style = { "--plane-color": meta.color } as CSSProperties;
                return (
                  <div
                    key={c.id}
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
                              className={`kw-chip ${kw === key ? "kw-chip-active" : ""}`}
                              title={k?.meaning}
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleKw(key);
                              }}
                            >
                              {k?.display ?? key}
                            </span>
                          );
                        })}
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
              })
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
    </div>
  );
}
