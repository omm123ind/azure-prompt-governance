import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../services/apiClient", () => ({
  getAuditLog: vi.fn(() =>
    Promise.resolve({
      count: 2,
      results: [
        {
          event_id_s: "evt-1",
          TimeGenerated: "2026-07-29T10:00:00Z",
          user_id_s: "hashed-user-1",
          action_taken_s: "block",
        },
        {
          event_id_s: "evt-2",
          TimeGenerated: "2026-07-29T10:01:00Z",
          user_id_s: "hashed-user-2",
          action_taken_s: "pass",
        },
      ],
    })
  ),
}));

import { LiveFeed } from "./LiveFeed";

describe("LiveFeed", () => {
  it("renders event cards with action badges", async () => {
    render(<LiveFeed />);
    await waitFor(() => {
      expect(screen.getByText("BLOCKED")).toBeInTheDocument();
      expect(screen.getByText("PASSED")).toBeInTheDocument();
    });
  });
});
