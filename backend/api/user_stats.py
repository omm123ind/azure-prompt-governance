import json
import os
from datetime import date, datetime

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient

from api.auth import require_role

_logs_client = None


def get_logs_client() -> LogsQueryClient:
    global _logs_client
    if _logs_client is None:
        _logs_client = LogsQueryClient(DefaultAzureCredential())
    return _logs_client


def build_user_spend_query(lookback_days: int = 7, top_n: int = 20) -> str:
    return "\n".join([
        f"let lookback = {lookback_days}d;",
        "PromptAuditLog_CL",
        "| where TimeGenerated > ago(lookback)",
        '| where action_taken_s != "anomaly"',
        "| summarize "
        "TotalCostUsd = sum(cost_usd_d), "
        "TotalPromptTokens = sum(prompt_tokens_d), "
        "TotalCompletionTokens = sum(completion_tokens_d) "
        "by user_id_s",
        f"| top {top_n} by TotalCostUsd desc",
    ])


def build_team_spend_query(lookback_days: int = 7) -> str:
    return "\n".join([
        f"let lookback = {lookback_days}d;",
        "PromptAuditLog_CL",
        "| where TimeGenerated > ago(lookback)",
        '| where action_taken_s != "anomaly"',
        "| summarize TotalCostUsd = sum(cost_usd_d) by team_id_s",
        "| order by TotalCostUsd desc",
    ])


def _json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def run_query(logs_client: LogsQueryClient, workspace_id: str, query: str) -> list:
    response = logs_client.query_workspace(workspace_id, query, timespan=None)
    table = response.tables[0]
    return [
        {col: _json_safe(val) for col, val in zip(table.columns, row)}
        for row in table.rows
    ]


def main(req: func.HttpRequest) -> func.HttpResponse:
    allowed, error_response = require_role(
        req,
        {"audit-viewer", "compliance-admin"},
        _decode_unverified=os.environ.get("RBAC_TEST_MODE") == "true",
    )
    if not allowed:
        return error_response

    try:
        scope = req.params.get("scope", "user")
        if scope not in ("user", "team"):
            raise ValueError("scope must be 'user' or 'team'")

        lookback_days_str = req.params.get("lookback_days", "7")
        lookback_days = int(lookback_days_str)
        if lookback_days <= 0:
            raise ValueError("lookback_days must be a positive integer")
    except ValueError as exc:
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            status_code=400,
            mimetype="application/json",
        )

    workspace_id = os.environ["AZURE_LOG_ANALYTICS_WORKSPACE_ID"]

    query = (
        build_user_spend_query(lookback_days=lookback_days)
        if scope == "user"
        else build_team_spend_query(lookback_days=lookback_days)
    )
    rows = run_query(get_logs_client(), workspace_id, query)
    return func.HttpResponse(
        json.dumps({"scope": scope, "results": rows}, default=_json_default),
        status_code=200,
        mimetype="application/json",
    )
