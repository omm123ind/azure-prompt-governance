import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { List, ListItem, ListItemText, Paper, Stack, Typography } from "@mui/material";

import { getUserStats, type UserStatsResponse } from "../services/apiClient";

export function CostAnalytics() {
  const [userSpend, setUserSpend] = useState<UserStatsResponse["results"]>([]);
  const [teamSpend, setTeamSpend] = useState<UserStatsResponse["results"]>([]);

  useEffect(() => {
    getUserStats("user").then((res) => setUserSpend(res.results));
    getUserStats("team").then((res) => setTeamSpend(res.results));
  }, []);

  const teamChartData = teamSpend.map((row) => ({
    team: String(row.team_id_s),
    cost: Number(row.TotalCostUsd ?? 0),
  }));

  return (
    <Stack spacing={3}>
      <Typography variant="h4" sx={{ fontWeight: 700 }}>
        Cost Analytics
      </Typography>
      <Paper sx={{ p: 2, height: 350 }}>
        <Typography variant="h6" gutterBottom>
          Cost by Team (last 7 days)
        </Typography>
        <ResponsiveContainer width="100%" height="85%">
          <BarChart data={teamChartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="team" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="cost" fill="#1976d2" />
          </BarChart>
        </ResponsiveContainer>
      </Paper>
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Top Users by Token Spend
        </Typography>
        <List>
          {userSpend.slice(0, 5).map((row) => (
            <ListItem key={String(row.user_id_s)}>
              <ListItemText
                primary={String(row.user_id_s)}
                secondary={`$${Number(row.TotalCostUsd ?? 0).toFixed(4)} — ${row.TotalPromptTokens ?? 0} prompt tokens`}
              />
            </ListItem>
          ))}
        </List>
      </Paper>
    </Stack>
  );
}
