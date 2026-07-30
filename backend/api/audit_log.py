import json
import os
import re
from datetime import datetime

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient

from api.auth import require_role

ALLOWED_ACTIONS = {"block", "flag", "pass", "anomaly"}
ALLOWED_FLAG_TYPES = {"pii", "jailbreak", "harm"}
ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-]{1,128}$")

_logs_client = None


def get_logs_client() -> LogsQueryClient:
    global _logs_client
    if _logs_client is None:
        _logs_client = LogsQueryClient(DefaultAzureCredential())
    return _logs_client


def _validate_id(value: str, field_name: str) -> str:
    if not ID_PATTERN.match(value):
        raise ValueError(f"invalid {field_name}: must be alphanumeric/hyphen, 1-128 chars")
    return value


def build_audit_search_query(
    start_time: str,
    end_time: str,
    user_id: str = "",
    team_id: str = "",
    action: str = "",
    flag_type: str = "",
) -> str:
    datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    datetime.fromisoformat(end_time.replace("Z", "+00:00"))

    if user_id:
        _validate_id(user_id, "user_id")
    if team_id:
        _validate_id(team_id, "team_id")
    if action and action not in ALLOWED_ACTIONS:
        raise ValueError(f"invalid action: must be one of {sorted(ALLOWED_ACTIONS)}")
    if flag_type and flag_type not in ALLOWED_FLAG_TYPES:
        raise ValueError(f"invalid flag_type: must be one of {sorted(ALLOWED_FLAG_TYPES)}")

    clauses = [
        "PromptAuditLog_CL",
        f'| where TimeGenerated between (datetime({start_time}) .. datetime({end_time}))',
    ]
    if user_id:
        clauses.append(f'| where user_id_s == "{user_id}"')
    if team_id:
        clauses.append(f'| where team_id_s == "{team_id}"')
    if action:
        clauses.append(f'| where action_taken_s == "{action}"')
    if flag_type == "pii":
        clauses.append("| where pii_detected_b == true")
    elif flag_type == "jailbreak":
        clauses.append("| where jailbreak_score_d > 0.6")
    elif flag_type == "harm":
        clauses.append(
            "| where harm_hate_score_d > 4 or harm_violence_score_d > 4 "
            "or harm_selfharm_score_d > 4 or harm_sexual_score_d > 4"
        )
    clauses.append("| order by TimeGenerated desc")
    clauses.append("| take 50")
    return "\n".join(clauses)


def run_query(logs_client: LogsQueryClient, workspace_id: str, query: str) -> list:
    response = logs_client.query_workspace(workspace_id, query, timespan=None)
    table = response.tables[0]
    return [dict(zip(table.columns, row)) for row in table.rows]


def main(req: func.HttpRequest) -> func.HttpResponse:
    allowed, error_response = require_role(
        req,
        {"audit-viewer", "compliance-admin"},
        _decode_unverified=os.environ.get("RBAC_TEST_MODE") == "true",
    )
    if not allowed:
        return error_response

    try:
        start_time = req.params.get("start_time")
        end_time = req.params.get("end_time")
        if not start_time or not end_time:
            raise ValueError("start_time and end_time query parameters are required")

        query = build_audit_search_query(
            start_time=start_time,
            end_time=end_time,
            user_id=req.params.get("user_id", ""),
            team_id=req.params.get("team_id", ""),
            action=req.params.get("action", ""),
            flag_type=req.params.get("flag_type", ""),
        )
    except ValueError as exc:
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            status_code=400,
            mimetype="application/json",
        )

    workspace_id = os.environ["AZURE_LOG_ANALYTICS_WORKSPACE_ID"]
    rows = run_query(get_logs_client(), workspace_id, query)
    return func.HttpResponse(
        json.dumps({"results": rows, "count": len(rows)}),
        status_code=200,
        mimetype="application/json",
    )
