import {
  AppBar,
  Toolbar,
  Typography,
  Chip,
  Box,
  Avatar,
} from "@mui/material";

import CloudDoneRoundedIcon from "@mui/icons-material/CloudDoneRounded";

import { drawerWidth } from "./Sidebar";

export default function Navbar() {
  return (
    <AppBar
      position="fixed"
      elevation={0}
      color="transparent"
      sx={{
        width: `calc(100% - ${drawerWidth}px)`,
        ml: `${drawerWidth}px`,
        backdropFilter: "blur(8px)",
        borderBottom: "1px solid #1e293b",
      }}
    >
      <Toolbar>

        <Typography
          variant="h5"
          sx={{
            flexGrow: 1,
            fontWeight: 700,
          }}
        >
          Azure AI Prompt Governance
        </Typography>

        <Box
          display="flex"
          gap={2}
          alignItems="center"
        >

          <Chip
            icon={<CloudDoneRoundedIcon />}
            label="Healthy"
            color="success"
          />

          <Avatar
            sx={{
              bgcolor: "#0078D4",
            }}
          >
            OA
          </Avatar>

        </Box>

      </Toolbar>
    </AppBar>
  );
}