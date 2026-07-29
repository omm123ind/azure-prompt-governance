import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("../auth/msalConfig", () => ({
  getUserRoles: vi.fn(),
}));

import { getUserRoles } from "../auth/msalConfig";
import { RequireRole } from "./RequireRole";

describe("RequireRole", () => {
  it("renders children when the user has the required role", () => {
    vi.mocked(getUserRoles).mockReturnValue(["compliance-admin"]);
    render(
      <MemoryRouter>
        <RequireRole role="compliance-admin">
          <div>Admin only content</div>
        </RequireRole>
      </MemoryRouter>
    );
    expect(screen.getByText("Admin only content")).toBeInTheDocument();
  });

  it("redirects when the user lacks the required role", () => {
    vi.mocked(getUserRoles).mockReturnValue(["audit-viewer"]);
    render(
      <MemoryRouter initialEntries={["/policy-manager"]}>
        <RequireRole role="compliance-admin">
          <div>Admin only content</div>
        </RequireRole>
      </MemoryRouter>
    );
    expect(screen.queryByText("Admin only content")).not.toBeInTheDocument();
  });
});
