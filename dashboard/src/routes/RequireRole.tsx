import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { getUserRoles } from "../auth/msalConfig";

export function RequireRole({ role, children }: { role: string; children: ReactNode }) {
  const roles = getUserRoles();
  if (!roles.includes(role)) {
    return <Navigate to="/audit-explorer" replace />;
  }
  return <>{children}</>;
}
