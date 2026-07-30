import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@azure/msal-react", () => ({
  MsalProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useIsAuthenticated: () => true,
  useMsal: () => ({ instance: { loginRedirect: vi.fn() }, accounts: [] }),
}));

import App from "./App";

describe("App", () => {
  it("renders the Live Feed view at the root route", () => {
    render(<App />);
    // "Live Feed" appears both as the Sidebar nav label and as the page
    // stub's content, so scope the query to the <main> region to avoid an
    // ambiguous multi-match from getByText.
    expect(within(screen.getByRole("main")).getByText("Live Feed")).toBeInTheDocument();
  });
});
