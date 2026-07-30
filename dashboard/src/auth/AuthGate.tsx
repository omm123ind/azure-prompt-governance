import type { ReactNode } from "react";
import { useIsAuthenticated, useMsal } from "@azure/msal-react";
import { Box, Button, Typography } from "@mui/material";

import { loginRequest } from "./msalConfig";

export function AuthGate({ children }: { children: ReactNode }) {
  const isAuthenticated = useIsAuthenticated();
  const { instance } = useMsal();

  if (!isAuthenticated) {
    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100vh",
          gap: 2,
        }}
      >
        <Typography variant="h5">Prompt Governance Platform</Typography>
        <Button variant="contained" onClick={() => instance.loginRedirect(loginRequest)}>
          Sign in
        </Button>
      </Box>
    );
  }

  return <>{children}</>;
}
