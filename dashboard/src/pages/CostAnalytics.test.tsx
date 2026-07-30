import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../services/apiClient", () => ({
  getUserStats: vi.fn((scope: string) =>
    Promise.resolve({
      scope,
      results:
        scope === "user"
          ? [{ user_id_s: "hashed-user-1", TotalCostUsd: 1.234, TotalPromptTokens: 5000 }]
          : [{ team_id_s: "hashed-team-1", TotalCostUsd: 4.5 }],
    })
  ),
}));

import { CostAnalytics } from "./CostAnalytics";

describe("CostAnalytics", () => {
  it("renders top users by spend", async () => {
    render(<CostAnalytics />);
    await waitFor(() => {
      expect(screen.getByText("hashed-user-1")).toBeInTheDocument();
    });
  });
});
