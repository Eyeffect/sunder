import { Fragment } from "react";
import { version } from "../../package.json";
import {
  CHANGE_COLOR,
  CHANGE_ICONS,
  CHANGE_LABEL,
  MILESTONES,
  MILESTONE_ICONS,
  ROADMAP,
  VERSIONS,
} from "../changelog";

export function ChangelogView() {
  const current = version;
  return (
    <div className="changelog-screen">
      <div className="changelog-page-title">CHANGELOG</div>

      <section className="milestone-strip" aria-label="Milestones">
        {MILESTONES.map((m, i) => {
          const Icon = MILESTONE_ICONS[m.status];
          return (
            <Fragment key={m.label}>
              <div className={`milestone-node ${m.status}`}>
                <div className="milestone-dot">
                  <Icon size={m.status === "planned" ? 12 : 14} />
                </div>
                <span className="milestone-label">{m.label}</span>
              </div>
              {i < MILESTONES.length - 1 && (
                <div className={`milestone-link ${m.status === "done" ? "lit" : ""}`} />
              )}
            </Fragment>
          );
        })}
      </section>

      <section className="changelog-body">
        <div className="version-log">
          <div className="changelog-section-title">VERSION LOG</div>
          {VERSIONS.map((v) => (
            <div key={v.version} className={`version-card${v.version === current ? " current" : ""}`}>
              <div className="version-head">
                <span className="version-tag">v{v.version}</span>
                <span className="version-codename">{v.codename}</span>
                {v.version === current && <span className="version-current-badge">CURRENT</span>}
                <span className="version-date">{v.date}</span>
              </div>
              <div className="version-changes">
                {v.changes.map((c, i) => {
                  const Icon = CHANGE_ICONS[c.type];
                  return (
                    <div key={i} className="change-row">
                      <Icon size={12} style={{ color: CHANGE_COLOR[c.type] }} />
                      <span className="change-type" style={{ color: CHANGE_COLOR[c.type] }}>
                        {CHANGE_LABEL[c.type]}
                      </span>
                      <span className="change-text">{c.text}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        <div className="roadmap">
          <div className="changelog-section-title">ON THE DIAL — ROADMAP</div>
          <div className="roadmap-list">
            {ROADMAP.map((r, i) => (
              <div key={i} className="roadmap-row">
                <span className={`status-pill ${r.status}`}>
                  {r.status === "in_progress" ? "INP" : "PLN"}
                </span>
                <span className="roadmap-text">{r.text}</span>
              </div>
            ))}
          </div>
          <div className="status-legend">
            <span className="status-pill in_progress">INP</span>
            <span>in progress</span>
            <span className="status-pill">PLN</span>
            <span>planned</span>
          </div>
          <div className="legend">
            {(Object.keys(CHANGE_ICONS) as (keyof typeof CHANGE_ICONS)[]).map((type) => {
              const Icon = CHANGE_ICONS[type];
              return (
                <div key={type} className="legend-row">
                  <Icon size={11} style={{ color: CHANGE_COLOR[type] }} />
                  <span className="legend-code" style={{ color: CHANGE_COLOR[type] }}>
                    {CHANGE_LABEL[type]}
                  </span>
                  <span className="legend-full">{type}</span>
                </div>
              );
            })}
          </div>
        </div>
      </section>
    </div>
  );
}
