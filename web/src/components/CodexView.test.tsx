import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CodexView } from "./CodexView";
import type { CodexCard, Keyword } from "../types";

const cards: CodexCard[] = [
  {
    id: "vg_001",
    name: "Vinyl Golem",
    set: "nf",
    plane: "neon",
    rarity: "COMMON",
    cost: 4,
    type: "BROADCAST",
    atk: 3,
    def: 5,
    keywords: [],
    rules: "ON_DEATH: +3 Signal.",
    flavor: "",
  },
  {
    id: "cw_001",
    name: "Cinder Hound",
    set: "cw",
    plane: "cinder",
    rarity: "COMMON",
    cost: 2,
    type: "BROADCAST",
    atk: 2,
    def: 2,
    keywords: ["LOUD"],
    rules: "LOUD — can attack the turn it airs.",
    flavor: "",
  },
];

const keywords: Keyword[] = [
  { key: "LOUD", display: "LOUD", meaning: "Can attack the turn it's aired.", kind: "flag" },
  {
    key: "RUSH",
    display: "RUSH",
    meaning: "Can attack Broadcasts immediately, but not the rival station.",
    kind: "flag",
  },
];

vi.stubGlobal(
  "fetch",
  vi.fn((url: string) => {
    const data = String(url).includes("/api/keywords") ? { keywords } : { cards };
    return Promise.resolve({ json: () => Promise.resolve(data) });
  }),
);

describe("CodexView", () => {
  it("renders keyword meanings on the KEYWORDS tab", async () => {
    render(<CodexView />);
    fireEvent.click(screen.getByRole("button", { name: "KEYWORDS" }));
    expect(
      await screen.findByText("Can attack the turn it's aired."),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Can attack Broadcasts immediately, but not the rival station.",
      ),
    ).toBeInTheDocument();
  });

  it("marks rarity and paints the plane-code watermark", async () => {
    render(<CodexView />);
    await screen.findByText("Cinder Hound");
    expect(screen.getAllByRole("img", { name: "Rarity: COMMON" })).toHaveLength(2);
    expect(document.querySelector(".card-watermark")?.textContent).toBe("FM");
  });

  it("filters cards when a keyword pill is clicked", async () => {
    render(<CodexView />);
    await screen.findByText("Cinder Hound");
    fireEvent.click(screen.getByRole("button", { name: "LOUD" }));
    expect(screen.getByText("Cinder Hound")).toBeInTheDocument();
    expect(screen.queryByText("Vinyl Golem")).not.toBeInTheDocument();
  });

  it("filters cards when a card keyword chip is clicked", async () => {
    render(<CodexView />);
    await screen.findByText("Cinder Hound");
    const chip = screen
      .getAllByText("LOUD")
      .find((el) => el.className.includes("kw-chip"));
    expect(chip).toBeDefined();
    fireEvent.click(chip!);
    expect(screen.getByText("Cinder Hound")).toBeInTheDocument();
    expect(screen.queryByText("Vinyl Golem")).not.toBeInTheDocument();
  });

  it("refreshes the registry after a successful generation", async () => {
    let registryCalls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        const u = String(url);
        if (u.includes("/api/registry")) {
          registryCalls += 1;
          const tags =
            registryCalls >= 2
              ? [{ id: "probe", definition: "a scan", reminder: "", status: "proposed" }]
              : [];
          return Promise.resolve({
            json: () => Promise.resolve({ tags, keywords: [] }),
          });
        }
        if (u.includes("/api/generate")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                cards: [],
                theme: "jazz club",
                seed: 1,
                mode: "llm",
              }),
          });
        }
        const data = u.includes("/api/keywords") ? { keywords } : { cards };
        return Promise.resolve({ json: () => Promise.resolve(data) });
      }),
    );
    render(<CodexView />);
    fireEvent.click(screen.getByRole("button", { name: "GENERATE" }));
    fireEvent.change(screen.getByLabelText("Theme"), {
      target: { value: "jazz club" },
    });
    fireEvent.click(screen.getByRole("button", { name: "TRANSMIT PACK" }));
    expect(await screen.findByText("probe")).toBeInTheDocument();
    expect(registryCalls).toBeGreaterThanOrEqual(2);
  });
});
