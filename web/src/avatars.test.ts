import { describe, expect, it } from "vitest";
import manifest from "../../sunder/cards/avatars.json";
import { DEFAULT_AVATAR, FALLBACK_AVATARS } from "./avatars";

describe("avatar manifest", () => {
  it("mirrors the server fallback list", () => {
    expect(FALLBACK_AVATARS).toEqual(manifest.avatars);
  });

  it("has unique ids and a valid default", () => {
    const ids = FALLBACK_AVATARS.map((a) => a.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(ids).toContain(DEFAULT_AVATAR);
  });
});
