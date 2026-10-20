import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { FALLBACK_AVATARS, type AvatarDef } from "../avatars";

export function AvatarPicker({
  current,
  ink,
  onPick,
  onClose,
}: {
  current: string;
  ink: string;
  onPick: (id: string) => void;
  onClose: () => void;
}) {
  const [avatars, setAvatars] = useState<AvatarDef[]>(FALLBACK_AVATARS);

  useEffect(() => {
    let alive = true;
    fetch("/api/avatars")
      .then((r) => r.json())
      .then((data) => {
        if (alive && Array.isArray(data?.avatars) && data.avatars.length > 0) {
          setAvatars(data.avatars);
        }
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const style = { "--avatar-ink": ink } as CSSProperties;

  return (
    <div className="overlay" onClick={onClose}>
      <div
        className="overlay-card avatar-picker"
        style={style}
        role="dialog"
        aria-modal="true"
        aria-label="Choose profile icon"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="avatar-picker-head">
          <span>PROFILE ICON</span>
          <button
            className="avatar-picker-close"
            type="button"
            onClick={onClose}
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <p className="avatar-picker-hint">
          Your sleeve's ink colours the icon.
        </p>
        <div className="avatar-picker-grid">
          {avatars.map((a) => (
            <button
              key={a.id}
              type="button"
              className={"avatar-option" + (a.id === current ? " active" : "")}
              onClick={() => onPick(a.id)}
              aria-pressed={a.id === current}
              title={a.label}
              autoFocus={a.id === current}
            >
              <span className="avatar-option-glyph">{a.glyph}</span>
              <span className="avatar-option-label">{a.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
