import manifestJson from "../../sunder/cards/sleeves.json";
import { allSleeves, setSleeves } from "./sleeves";
import type { Sleeve, SleeveDef } from "./sleeves";

/** Load the real server manifest (sunder/cards/sleeves.json) into the
  client registry and return the hydrated sleeves — shared by tests that
  must agree with what the backend will actually serve. */
export function importServerManifest(): Sleeve[] {
  setSleeves(manifestJson.sleeves as SleeveDef[]);
  return allSleeves();
}

/** The pattern catalog shipped in the server manifest (`patterns` key). */
export function manifestPatterns(): string[] {
  const arr = (manifestJson as unknown as { patterns?: string[] }).patterns;
  return Array.isArray(arr) ? arr : [];
}
