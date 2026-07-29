import { useEffect, useState } from "react";
import {
  Paper,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Chip,
  Typography,
} from "@mui/material";
import { api } from "../services/api";

interface AuditLog {
  timestamp: string;
  prompt: string;
  allowed: boolean;
  risk_level: string;
  model: string;
}

export default function AuditTable() {
  const [logs, setLogs] = useState<AuditLog[]>([]);

  async function loadLogs() {
    try {
      const res = await api.get("/audit");
      setLogs(res.data);
    } catch (err) {
      console.error(err);
    }
  }

  useEffect(() => {
    loadLogs();

    const timer = setInterval(loadLogs, 5000);

    return () => clearInterval(timer);
  }, []);

  return (
    <Paper sx={{ p: 2 }}>

      <Typography variant="h6" sx={{ mb: 2 }}>
        Recent Audit Events
      </Typography>

      <Table>

        <TableHead>

          <TableRow>
            <TableCell>Time</TableCell>
            <TableCell>Risk</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Model</TableCell>
            <TableCell>Prompt</TableCell>
          </TableRow>

        </TableHead>

        <TableBody>

          {logs.map((log, index) => (

            <TableRow key={index}>

              <TableCell>
                {new Date(log.timestamp).toLocaleString()}
              </TableCell>

              <TableCell>

                <Chip
                  label={log.risk_level}
                  color={
                    log.risk_level === "High"
                      ? "error"
                      : log.risk_level === "Medium"
                      ? "warning"
                      : "success"
                  }
                />

              </TableCell>

              <TableCell>

                <Chip
                  label={
                    log.allowed
                      ? "Allowed"
                      : "Blocked"
                  }
                  color={
                    log.allowed
                      ? "success"
                      : "error"
                  }
                />

              </TableCell>

              <TableCell>
                {log.model}
              </TableCell>

              <TableCell>
                {log.prompt.substring(0, 60)}...
              </TableCell>

            </TableRow>

          ))}

        </TableBody>

      </Table>

    </Paper>
  );
}