/** PvP session persistence + invite links (docs/multiplayer.md).
 *
 * The seat token is a bearer secret: it lives in sessionStorage (per tab, gone
 * when the tab closes) so a refresh can `resume`, and it is never rendered.
 */

export const PVP_KEY = "sunder-pvp";

export interface PvpSession {
  code: string;
  token: string;
}

export function loadPvp(): PvpSession | null {
  try {
    const raw = sessionStorage.getItem(PVP_KEY);
    if (!raw) return null;
    const v = JSON.parse(raw) as Partial<PvpSession>;
    return typeof v.code === "string" && typeof v.token === "string"
      ? { code: v.code, token: v.token }
      : null;
  } catch {
    return null;
  }
}

export function savePvp(s: PvpSession): void {
  try {
    sessionStorage.setItem(PVP_KEY, JSON.stringify(s));
  } catch {
    /* storage unavailable — refresh just won't resume */
  }
}

export function clearPvp(): void {
  try {
    sessionStorage.removeItem(PVP_KEY);
  } catch {
    /* ignore */
  }
}

const CODE_RE = /^[A-Z0-9]{4,12}$/;

export function normalizeCode(raw: string): string {
  return raw.trim().toUpperCase().replace(/[^A-Z0-9]/g, "");
}

/** `?room=CODE` from the current URL, if present and well-formed. */
export function roomFromUrl(search: string = window.location.search): string | null {
  const code = normalizeCode(new URLSearchParams(search).get("room") ?? "");
  return CODE_RE.test(code) ? code : null;
}

export function inviteLink(code: string, loc: Location = window.location): string {
  return `${loc.origin}${loc.pathname}?room=${encodeURIComponent(code)}`;
}

/** Drop `?room=` from the address bar without reloading. */
export function clearRoomFromUrl(): void {
  try {
    const url = new URL(window.location.href);
    if (!url.searchParams.has("room")) return;
    url.searchParams.delete("room");
    window.history.replaceState(null, "", url.toString());
  } catch {
    /* ignore */
  }
}

export function endReasonText(reason: string | null | undefined, won: boolean): string {
  switch (reason) {
    case "concede":
      return won ? "The rival conceded." : "You conceded.";
    case "timeout":
      return won ? "The rival ran out of time." : "You ran out of time.";
    case "disconnect":
      return won ? "The rival lost their connection." : "You were disconnected too long.";
    default:
      return "";
  }
}
