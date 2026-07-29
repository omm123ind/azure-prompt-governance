import { useEffect, useState } from "react";
import { Box, Button, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";

import { getAuditLog, type AuditLogFilters, type AuditLogResponse } from "../services/apiClient";

const COLUMNS: GridColDef[] = [
  { field: "TimeGenerated", headerName: "Time", flex: 1 },
  { field: "user_id_s", headerName: "User", flex: 1 },
  { field: "team_id_s", headerName: "Team", flex: 1 },
  { field: "action_taken_s", headerName: "Action", flex: 1 },
  { field: "prompt_hash_s", headerName: "Prompt Hash", flex: 1.5 },
];

function defaultFilters(): AuditLogFilters {
  const end = new Date();
  const start = new Date(end.getTime() - 24 * 60 * 60 * 1000);
  return { startTime: start.toISOString(), endTime: end.toISOString() };
}

function toCsv(rows: AuditLogResponse["results"]): string {
  if (rows.length === 0) return "";
  const headers = Object.keys(rows[0]);
  const lines = rows.map((row) => headers.map((h) => JSON.stringify(row[h] ?? "")).join(","));
  return [headers.join(","), ...lines].join("\n");
}

export function AuditExplorer() {
  const [filters, setFilters] = useState<AuditLogFilters>(defaultFilters());
  const [rows, setRows] = useState<AuditLogResponse["results"]>([]);

  async function search() {
    const { results } = await getAuditLog(filters);
    setRows(results);
  }

  useEffect(() => {
    search();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function exportCsv() {
    const csv = toCsv(rows);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "audit-log-export.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Stack spacing={2}>
      <Typography variant="h4" fontWeight={700}>
        Audit Explorer
      </Typography>
      <Stack direction="row" spacing={2}>
        <TextField
          select
          label="Action"
          size="small"
          value={filters.action ?? ""}
          onChange={(e) => setFilters({ ...filters, action: e.target.value || undefined })}
          sx={{ minWidth: 150 }}
        >
          <MenuItem value="">All</MenuItem>
          <MenuItem value="block">Block</MenuItem>
          <MenuItem value="flag">Flag</MenuItem>
          <MenuItem value="pass">Pass</MenuItem>
        </TextField>
        <TextField
          select
          label="Flag type"
          size="small"
          value={filters.flagType ?? ""}
          onChange={(e) => setFilters({ ...filters, flagType: e.target.value || undefined })}
          sx={{ minWidth: 150 }}
        >
          <MenuItem value="">All</MenuItem>
          <MenuItem value="pii">PII</MenuItem>
          <MenuItem value="jailbreak">Jailbreak</MenuItem>
          <MenuItem value="harm">Harm</MenuItem>
        </TextField>
        <TextField
          label="User ID"
          size="small"
          value={filters.userId ?? ""}
          onChange={(e) => setFilters({ ...filters, userId: e.target.value || undefined })}
        />
        <Button variant="contained" onClick={search}>
          Search
        </Button>
        <Button variant="outlined" onClick={exportCsv}>
          Export CSV
        </Button>
      </Stack>
      <Box sx={{ height: 500 }}>
        <DataGrid
          rows={rows}
          columns={COLUMNS}
          getRowId={(row) => String(row.event_id_s)}
          pageSizeOptions={[50]}
          initialState={{ pagination: { paginationModel: { pageSize: 50 } } }}
        />
      </Box>
    </Stack>
  );
}
