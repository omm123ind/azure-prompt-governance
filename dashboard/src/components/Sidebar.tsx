import {
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
} from "@mui/material";
import DashboardIcon from "@mui/icons-material/Dashboard";
import SearchIcon from "@mui/icons-material/Search";
import PolicyIcon from "@mui/icons-material/Policy";
import BarChartIcon from "@mui/icons-material/BarChart";
import { Link, useLocation } from "react-router-dom";
import { useMsal } from "@azure/msal-react";

export const drawerWidth = 240;

const NAV_ITEMS = [
  { label: "Live Feed", path: "/", icon: <DashboardIcon /> },
  { label: "Audit Explorer", path: "/audit-explorer", icon: <SearchIcon /> },
  { label: "Policy Manager", path: "/policy-manager", icon: <PolicyIcon /> },
  { label: "Cost Analytics", path: "/cost-analytics", icon: <BarChartIcon /> },
];

export function Sidebar() {
  const location = useLocation();
  const { accounts } = useMsal();
  const userName = accounts[0]?.name ?? accounts[0]?.username ?? "";

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: "border-box" },
      }}
    >
      <Toolbar>
        <Typography variant="h6" component="div" noWrap>
          Prompt Governance
        </Typography>
      </Toolbar>
      <Box sx={{ px: 2, pb: 1 }}>
        <Typography variant="body2" color="text.secondary" component="div" noWrap>
          {userName}
        </Typography>
      </Box>
      <List>
        {NAV_ITEMS.map((item) => (
          <ListItemButton
            key={item.path}
            component={Link}
            to={item.path}
            selected={location.pathname === item.path}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
    </Drawer>
  );
}
