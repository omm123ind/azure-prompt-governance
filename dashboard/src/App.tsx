import { Box, Toolbar } from "@mui/material";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { MsalProvider } from "@azure/msal-react";

import { msalInstance } from "./auth/msalConfig";
import { AuthGate } from "./auth/AuthGate";
import { Sidebar, drawerWidth } from "./components/Sidebar";
import { RequireRole } from "./routes/RequireRole";
import { LiveFeed } from "./pages/LiveFeed";
import { AuditExplorer } from "./pages/AuditExplorer";
import { PolicyManager } from "./pages/PolicyManager";
import { CostAnalytics } from "./pages/CostAnalytics";

export default function App() {
  return (
    <MsalProvider instance={msalInstance}>
      <AuthGate>
        <BrowserRouter>
          <Box sx={{ display: "flex" }}>
            <Sidebar />
            <Box component="main" sx={{ flexGrow: 1, ml: `${drawerWidth}px`, p: 3 }}>
              <Toolbar />
              <Routes>
                <Route path="/" element={<LiveFeed />} />
                <Route path="/audit-explorer" element={<AuditExplorer />} />
                <Route
                  path="/policy-manager"
                  element={
                    <RequireRole role="compliance-admin">
                      <PolicyManager />
                    </RequireRole>
                  }
                />
                <Route path="/cost-analytics" element={<CostAnalytics />} />
              </Routes>
            </Box>
          </Box>
        </BrowserRouter>
      </AuthGate>
    </MsalProvider>
  );
}
