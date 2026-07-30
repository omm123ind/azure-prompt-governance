import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@azure/msal-react", () => ({
  useIsAuthenticated: vi.fn(),
  useMsal: vi.fn(() => ({
    instance: { loginRedirect: vi.fn() },
  })),
}));

import { useIsAuthenticated } from "@azure/msal-react";
import { AuthGate } from "./AuthGate";

describe("AuthGate", () => {
  it("shows a login button when not authenticated", () => {
    vi.mocked(useIsAuthenticated).mockReturnValue(false);
    render(
      <AuthGate>
        <div>Protected content</div>
      </AuthGate>
    );
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
  });

  it("renders children when authenticated", () => {
    vi.mocked(useIsAuthenticated).mockReturnValue(true);
    render(
      <AuthGate>
        <div>Protected content</div>
      </AuthGate>
    );
    expect(screen.getByText("Protected content")).toBeInTheDocument();
  });
});
