import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearPvp,
  endReasonText,
  inviteLink,
  loadPvp,
  normalizeCode,
  PVP_KEY,
  roomFromUrl,
  savePvp,
} from "./pvp";

const store = new Map<string, string>();
vi.stubGlobal("sessionStorage", {
  getItem: (k: string) => store.get(k) ?? null,
  setItem: (k: string, v: string) => void store.set(k, v),
  removeItem: (k: string) => void store.delete(k),
});

beforeEach(() => store.clear());

describe("pvp session", () => {
  it("round-trips code + token through sessionStorage", () => {
    expect(loadPvp()).toBeNull();
    savePvp({ code: "ABC234", token: "secret" });
    expect(loadPvp()).toEqual({ code: "ABC234", token: "secret" });
    clearPvp();
    expect(loadPvp()).toBeNull();
  });

  it("ignores malformed storage", () => {
    store.set(PVP_KEY, "{not json");
    expect(loadPvp()).toBeNull();
    store.set(PVP_KEY, JSON.stringify({ code: 5 }));
    expect(loadPvp()).toBeNull();
  });
});

describe("room codes and links", () => {
  it("normalizes user input", () => {
    expect(normalizeCode("  abc-234 ")).toBe("ABC234");
  });

  it("reads ?room= from the URL and rejects junk", () => {
    expect(roomFromUrl("?room=abc234")).toBe("ABC234");
    expect(roomFromUrl("?room=<script>")).toBe("SCRIPT");
    expect(roomFromUrl("?room=a")).toBeNull();
    expect(roomFromUrl("")).toBeNull();
  });

  it("builds an invite link on the current page", () => {
    const loc = { origin: "https://sunder.lab", pathname: "/" } as Location;
    expect(inviteLink("ABC234", loc)).toBe("https://sunder.lab/?room=ABC234");
  });
});

describe("endReasonText", () => {
  it("phrases each reason from the viewer's side", () => {
    expect(endReasonText("concede", true)).toBe("The rival conceded.");
    expect(endReasonText("concede", false)).toBe("You conceded.");
    expect(endReasonText("timeout", false)).toBe("You ran out of time.");
    expect(endReasonText("disconnect", true)).toBe("The rival lost their connection.");
    expect(endReasonText("signal", true)).toBe("");
    expect(endReasonText(null, true)).toBe("");
  });
});
