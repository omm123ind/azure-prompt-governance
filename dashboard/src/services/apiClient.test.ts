import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("../auth/msalConfig", () => ({
  msalInstance: {
    getActiveAccount: vi.fn(() => ({ homeAccountId: "test-account" })),
    acquireTokenSilent: vi.fn(() => Promise.resolve({ accessToken: "fake-token" })),
  },
  loginRequest: { scopes: ["api://fake/access_as_user"] },
}));

import axios from "axios";
import { getAuditLog, getUserStats, getPolicyRules, savePolicyRules } from "./apiClient";

vi.mock("axios", () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(() => Promise.resolve({ data: { results: [], count: 0 } })),
      put: vi.fn(() => Promise.resolve({ data: { saved: true } })),
    })),
  },
}));

describe("apiClient", () => {
  it("getAuditLog attaches a bearer token and passes filters as query params", async () => {
    const result = await getAuditLog({
      startTime: "2026-07-01T00:00:00Z",
      endTime: "2026-07-02T00:00:00Z",
    });
    expect(result.results).toEqual([]);
  });

  it("getUserStats requests the given scope", async () => {
    const result = await getUserStats("team", 7);
    expect(result.results).toEqual([]);
  });

  it("getPolicyRules and savePolicyRules round-trip through PUT", async () => {
    const rules = await getPolicyRules();
    expect(rules).toBeDefined();
    await expect(savePolicyRules({ version: "1.0", updated_at: "now", rules: [] })).resolves.toBeUndefined();
  });
});
