import {
  Grid,
  Card,
  CardContent,
  Typography
} from "@mui/material";

export interface DashboardStats {
  total: number;
  allowed: number;
  blocked: number;
  high_risk: number;
  medium_risk: number;
  low_risk: number;
}

interface Props {
  stats: DashboardStats;
}

export default function KpiCards({ stats }: Props) {
  const cards = [
    { title: "Total Requests", value: stats.total },
    { title: "Allowed", value: stats.allowed },
    { title: "Blocked", value: stats.blocked },
    { title: "High Risk", value: stats.high_risk },
  ];

  return (
    <Grid container spacing={3} sx={{ mb: 4 }}>
      {cards.map((card) => (
        <Grid key={card.title} xs={12} sm={6} md={3}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                {card.title}
              </Typography>

              <Typography variant="h3" sx={{ mt: 1, fontWeight: 700 }}>
                {card.value}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}