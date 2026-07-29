import {
  Drawer,
  Toolbar,
  Typography,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Box,
} from "@mui/material";

import DashboardRoundedIcon from "@mui/icons-material/DashboardRounded";
import ShieldRoundedIcon from "@mui/icons-material/ShieldRounded";
import PolicyRoundedIcon from "@mui/icons-material/PolicyRounded";
import AnalyticsRoundedIcon from "@mui/icons-material/AnalyticsRounded";
import SettingsRoundedIcon from "@mui/icons-material/SettingsRounded";

export const drawerWidth = 240;

const menu = [
  {
    title: "Dashboard",
    icon: <DashboardRoundedIcon />,
  },
  {
    title: "Audit Explorer",
    icon: <ShieldRoundedIcon />,
  },
  {
    title: "Policies",
    icon: <PolicyRoundedIcon />,
  },
  {
    title: "Analytics",
    icon: <AnalyticsRoundedIcon />,
  },
  {
    title: "Settings",
    icon: <SettingsRoundedIcon />,
  },
];

export default function Sidebar() {
  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,

        "& .MuiDrawer-paper": {
          width: drawerWidth,
          boxSizing: "border-box",
          background: "#0f172a",
          borderRight: "1px solid #1e293b",
        },
      }}
    >
      <Toolbar>
        <Box>

          <Typography
            variant="h6"
            fontWeight={700}
          >
            Azure AI
          </Typography>

          <Typography
            variant="body2"
            color="text.secondary"
          >
            Prompt Governance
          </Typography>

        </Box>
      </Toolbar>

      <Divider />

      <List>

        {menu.map((item, index) => (

          <ListItemButton
            key={index}
            selected={index === 0}
          >

            <ListItemIcon>

              {item.icon}

            </ListItemIcon>

            <ListItemText
              primary={item.title}
            />

          </ListItemButton>

        ))}

      </List>

    </Drawer>
  );
}