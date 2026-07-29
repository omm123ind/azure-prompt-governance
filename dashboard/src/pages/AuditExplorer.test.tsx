import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../services/apiClient", () => ({
  getAuditLog: vi.fn(() =>
    Promise.resolve({
      count: 1,
      results: [
        {
          event_id_s: "evt-1",
          TimeGenerated: "2026-07-29T10:00:00Z",
          user_id_s: "hashed-user-1",
          action_taken_s: "block",
          prompt_hash_s: "a".repeat(64),
        },
      ],
    })
  ),
}));

import { AuditExplorer } from "./AuditExplorer";

describe("AuditExplorer", () => {
  it("renders results in a table and never shows raw prompt text", async () => {
    render(<AuditExplorer />);
    await waitFor(() => {
      expect(screen.getByText("hashed-user-1")).toBeInTheDocument();
    });
    expect(screen.queryByText(/my email is/i)).not.toBeInTheDocument();
  });
});
