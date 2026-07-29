import { useEffect, useState } from "react";

import {
  Box,
  Toolbar,
  Container,
  Grid,
  Paper,
  Typography,
} from "@mui/material";

import Sidebar, {
  drawerWidth,
} from "../components/Sidebar";

import Navbar from "../components/Navbar";

import KpiCards, {
  type DashboardStats,
} from "../components/KpiCards";

import RiskChart from "../components/RiskChart";

import AuditTable from "../components/AuditTable";

import { api } from "../services/api";

export default function Dashboard() {

  const [stats, setStats] =
    useState<DashboardStats>({
      total: 0,
      allowed: 0,
      blocked: 0,
      high_risk: 0,
      medium_risk: 0,
      low_risk: 0,
    });

  async function loadStats() {

    try {

      const res =
        await api.get("/stats");

      setStats(res.data);

    } catch (err) {

      console.error(err);

    }

  }

  useEffect(() => {

    loadStats();

    const timer =
      setInterval(loadStats, 5000);

    return () =>
      clearInterval(timer);

  }, []);

  return (

    <Box sx={{ display: "flex" }}>

      <Sidebar />

      <Navbar />

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          ml: `${drawerWidth}px`,
        }}
      >

        <Toolbar />

        <Container
          maxWidth="xl"
          sx={{
            mt: 4,
            mb: 5,
          }}
        >

          <Typography
            variant="h4"
            fontWeight={700}
            gutterBottom
          >
            Dashboard
          </Typography>

          <Typography
            color="text.secondary"
            sx={{ mb: 4 }}
          >
            Enterprise Prompt Governance Platform
          </Typography>

          <KpiCards
            stats={stats}
          />

          <Grid
            container
            spacing={3}
          >

            <Grid
              xs={12}
              lg={4}
            >

              <Paper
                sx={{
                  p: 3,
                  height: 420,
                }}
              >

                <Typography
                  variant="h6"
                  gutterBottom
                >
                  Risk Distribution
                </Typography>

                <RiskChart
                  high={stats.high_risk}
                  medium={stats.medium_risk}
                  low={stats.low_risk}
                />

              </Paper>

            </Grid>

            <Grid
              xs={12}
              lg={8}
            >

              <AuditTable />

            </Grid>

          </Grid>

        </Container>

      </Box>

    </Box>

  );

}