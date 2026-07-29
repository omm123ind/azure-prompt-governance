import { useEffect, useState } from "react"

import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
} from "@mui/material"

import { api } from "../services/api"

interface AuditLog {
  timestamp: string
  allowed: boolean
  risk_level: string
  model: string
}

export default function AuditExplorer() {

  const [logs, setLogs] = useState<AuditLog[]>([])

  async function loadLogs() {
    try {
      const res = await api.get("/audit")
      setLogs(res.data)
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {

    loadLogs()

    const timer = setInterval(loadLogs, 5000)

    return () => clearInterval(timer)

  }, [])

  return (

    <TableContainer component={Paper}>

      <Table>

        <TableHead>

          <TableRow>

            <TableCell>Time</TableCell>

            <TableCell>Risk</TableCell>

            <TableCell>Status</TableCell>

            <TableCell>Model</TableCell>

          </TableRow>

        </TableHead>

        <TableBody>

          {logs.map((log, index) => (

            <TableRow key={index}>

              <TableCell>
                {new Date(log.timestamp).toLocaleString()}
              </TableCell>

              <TableCell>
                {log.risk_level}
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

            </TableRow>

          ))}

        </TableBody>

      </Table>

    </TableContainer>

  )

}