import axios from "axios";

import { loginRequest, msalInstance } from "../auth/msalConfig";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL as string,
});

async function authHeader(): Promise<Record<string, string>> {
  const account = msalInstance.getActiveAccount();
  if (!account) return {};
  const result = await msalInstance.acquireTokenSilent({ ...loginRequest, account });
  return { Authorization: `Bearer ${result.accessToken}` };
}

export interface AuditLogFilters {
  startTime: string;
  endTime: string;
  userId?: string;
  teamId?: string;
  action?: string;
  flagType?: string;
}

export interface AuditLogResponse {
  results: Record<string, unknown>[];
  count: number;
}

export async function getAuditLog(filters: AuditLogFilters): Promise<AuditLogResponse> {
  const headers = await authHeader();
  const params = {
    start_time: filters.startTime,
    end_time: filters.endTime,
    user_id: filters.userId,
    team_id: filters.teamId,
    action: filters.action,
    flag_type: filters.flagType,
  };
  const response = await client.get<AuditLogResponse>("/audit_log", { headers, params });
  return response.data;
}

export interface UserStatsResponse {
  scope: "user" | "team";
  results: Record<string, unknown>[];
}

export async function getUserStats(
  scope: "user" | "team",
  lookbackDays = 7
): Promise<UserStatsResponse> {
  const headers = await authHeader();
  const response = await client.get<UserStatsResponse>("/user_stats", {
    headers,
    params: { scope, lookback_days: lookbackDays },
  });
  return response.data;
}

export interface PolicyRule {
  id: string;
  description: string;
  condition: string;
  threshold: number;
  action: "block" | "flag" | "pass";
  notify: boolean;
  enabled: boolean;
}

export interface PolicyRules {
  version: string;
  updated_at: string;
  rules: PolicyRule[];
}

export async function getPolicyRules(): Promise<PolicyRules> {
  const headers = await authHeader();
  const response = await client.get<PolicyRules>("/policy_config", { headers });
  return response.data;
}

export async function savePolicyRules(rules: PolicyRules): Promise<void> {
  const headers = await authHeader();
  await client.put("/policy_config", rules, { headers });
}
