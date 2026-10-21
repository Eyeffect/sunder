import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LobbyView } from "./LobbyView";

const noop = () => {};

describe("LobbyView", () => {
  it("creates a room", () => {
    const onCreate = vi.fn();
    render(<LobbyView room={null} inPvp={false} onCreate={onCreate} onJoin={noop}
      onCancel={noop} onBack={noop} />);
    fireEvent.click(screen.getByRole("button", { name: "CREATE ROOM" }));
    expect(onCreate).toHaveBeenCalled();
  });

  it("joins with a normalized code and blocks empty submits", () => {
    const onJoin = vi.fn();
    render(<LobbyView room={null} inPvp={false} onCreate={noop} onJoin={onJoin}
      onCancel={noop} onBack={noop} />);
    const btn = screen.getByRole("button", { name: "JOIN ROOM" });
    expect(btn).toBeDisabled();
    fireEvent.change(screen.getByLabelText("JOIN"), { target: { value: "abc 234" } });
    fireEvent.click(btn);
    expect(onJoin).toHaveBeenCalledWith("ABC234");
  });

  it("shows the code while waiting and can cancel", () => {
    const onCancel = vi.fn();
    render(<LobbyView
      room={{ mode: "pvp", code: "ABC234", seat: null, token: null, status: "waiting" }}
      inPvp={false} onCreate={noop} onJoin={noop} onCancel={onCancel} onBack={noop} />);
    expect(screen.getByTestId("room-code")).toHaveTextContent("ABC234");
    fireEvent.click(screen.getByRole("button", { name: "CANCEL" }));
    expect(onCancel).toHaveBeenCalled();
  });

  it("sends you back to a live match instead of offering a new one", () => {
    const onBack = vi.fn();
    render(<LobbyView
      room={{ mode: "pvp", code: "ABC234", seat: 0, token: "t", status: "live" }}
      inPvp onCreate={noop} onJoin={noop} onCancel={noop} onBack={onBack} />);
    expect(screen.queryByRole("button", { name: "CREATE ROOM" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "BACK TO THE DUEL" }));
    expect(onBack).toHaveBeenCalled();
  });
});
