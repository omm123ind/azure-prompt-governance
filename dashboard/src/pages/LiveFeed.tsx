import { useEffect, useState } from "react";
import { Card, CardContent, Chip, Stack, Typography } from "@mui/material";

import { getAuditLog, type AuditLogResponse } from "../services/apiClient";

const ACTION_LABELS: Record<string, string> = {
  block: "BLOCKED",
  flag: "FLAGGED",
  pass: "PASSED",
  anomaly: "ANOMALY",
};

const ACTION_COLORS: Record<string, "error" | "warning" | "default" | "info"> = {
  block: "error",
  flag: "warning",
  pass: "default",
  anomaly: "info",
};

function lastDay(): { startTime: string; endTime: string } {
  const end = new Date();
  const start = new Date(end.getTime() - 24 * 60 * 60 * 1000);
  return { startTime: start.toISOString(), endTime: end.toISOString() };
}

export function LiveFeed() {
  const [events, setEvents] = useState<AuditLogResponse["results"]>([]);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const { results } = await getAuditLog(lastDay());
        if (!cancelled) setEvents(results);
      } catch (err) {
        console.error("Live Feed poll failed", err);
      }
    }

    poll();
    const timer = setInterval(poll, 3000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  return (
    <Stack spacing={2}>
      <Typography variant="h4" fontWeight={700}>
        Live Feed
      </Typography>
      {events.map((event) => {
        const action = String(event.action_taken_s ?? "pass");
        return (
          <Card key={String(event.event_id_s)} variant="outlined">
            <CardContent>
              <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
                <Chip label={ACTION_LABELS[action] ?? action.toUpperCase()} color={ACTION_COLORS[action] ?? "default"} />
                <Typography variant="body2" color="text.secondary">
                  {String(event.TimeGenerated ?? "")}
                </Typography>
                <Typography variant="body2">{String(event.user_id_s ?? "")}</Typography>
              </Stack>
            </CardContent>
          </Card>
        );
      })}
    </Stack>
  );
}
