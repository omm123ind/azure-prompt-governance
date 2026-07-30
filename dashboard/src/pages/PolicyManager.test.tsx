import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const mockRules = {
  version: "1.0",
  updated_at: "2026-07-19T00:00:00Z",
  rules: [
    {
      id: "block_pii",
      description: "Block prompts with high-confidence PII detection",
      condition: "pii_confidence",
      threshold: 0.8,
      action: "block" as const,
      notify: true,
      enabled: true,
    },
  ],
};

vi.mock("../services/apiClient", () => ({
  getPolicyRules: vi.fn(() => Promise.resolve(mockRules)),
  savePolicyRules: vi.fn(() => Promise.resolve()),
}));

import { getPolicyRules, savePolicyRules } from "../services/apiClient";
import { PolicyManager } from "./PolicyManager";

describe("PolicyManager", () => {
  it("renders rules and saves edits", async () => {
    render(<PolicyManager />);
    await waitFor(() => {
      expect(screen.getByText(/block prompts with high-confidence pii detection/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(savePolicyRules).toHaveBeenCalledTimes(1);
    });
    expect(getPolicyRules).toHaveBeenCalledTimes(1);
  });
});
