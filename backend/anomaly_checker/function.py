import json
import logging
import os
import uuid
from datetime import datetime, timezone

import azure.functions as func
import requests
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient
from azure.storage.blob import BlobServiceClient

from log_writer.function import hash_text, publish_to_event_hub
from shared.constants import ANOMALY_MULTIPLIER
from shared.models import AuditEvent

_logs_client = None


def get_logs_client() -> LogsQueryClient:
    global _logs_client
    if _logs_client is None:
        _logs_client = LogsQueryClient(DefaultAzureCredential())
    return _logs_client


def get_active_users_24h(logs_client: LogsQueryClient, workspace_id: str) -> dict:
    query = "\n".join([
        "PromptAuditLog_CL",
        "| where TimeGenerated > ago(24h)",
        '| where action_taken_s != "anomaly"',
        "| summarize TotalTokens = sum(prompt_tokens_d + completion_tokens_d) by user_id_s",
    ])
    response = logs_client.query_workspace(workspace_id, query, timespan=None)
    table = response.tables[0]
    rows = [dict(zip(table.columns, row)) for row in table.rows]
    return {row["user_id_s"]: int(row["TotalTokens"]) for row in rows}


def _baseline_blob_client():
    conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container_name = os.environ.get("ANOMALY_BASELINE_CONTAINER", "governance-policies")
    blob_name = os.environ.get("ANOMALY_BASELINE_BLOB", "usage-baselines.json")
    service = BlobServiceClient.from_connection_string(conn_str)
    return service.get_container_client(container_name).get_blob_client(blob_name)


def load_baselines() -> dict:
    blob = _baseline_blob_client()
    try:
        return json.loads(blob.download_blob().readall())
    except Exception:
        return {}


def save_baselines(baselines: dict) -> None:
    """Overwrite the baseline blob with the full snapshot.

    Assumes at-most-one concurrent invocation (true today, since this is driven by a
    single timer trigger). If this function is ever deployed with multiple concurrent
    instances, this read-modify-write needs an ETag-conditional upload to avoid a
    lost-update race between overlapping runs.
    """
    blob = _baseline_blob_client()
    blob.upload_blob(json.dumps(baselines), overwrite=True)


def update_rolling_baseline(previous_baseline: float, today_total: int, decay: float = 1 / (7 * 24)) -> float:
    if previous_baseline == 0:
        return float(today_total)
    return (previous_baseline * (1 - decay)) + (today_total * decay)


def is_anomalous(today_total: int, baseline: float) -> bool:
    return baseline > 0 and today_total > baseline * ANOMALY_MULTIPLIER


def build_anomaly_event(user_id: str, today_total: int, baseline: float) -> AuditEvent:
    # Invariant: synthetic audit rows (like this anomaly event) must never contribute to
    # any usage or cost aggregate. That's why prompt_tokens/completion_tokens are zeroed
    # below (the triggering token count is preserved in block_reason instead), and why
    # every summary query over PromptAuditLog_CL excludes action_taken_s == "anomaly".
    return AuditEvent(
        event_id=str(uuid.uuid4()),
        session_id=str(uuid.uuid4()),
        user_id=user_id,
        team_id="unassigned",
        prompt_hash=hash_text(f"anomaly-check-{user_id}-{today_total}"),
        response_hash=hash_text(""),
        pii_detected=False,
        pii_confidence=0.0,
        pii_categories=[],
        jailbreak_score=0.0,
        harm_hate_score=0,
        harm_violence_score=0,
        harm_selfharm_score=0,
        harm_sexual_score=0,
        action_taken="anomaly",
        block_reason=(
            f"24h token usage {today_total} exceeded "
            f"{ANOMALY_MULTIPLIER}x baseline {baseline:.1f}"
        ),
        prompt_tokens=0,
        completion_tokens=0,
        cost_usd=0.0,
        model="n/a",
        latency_ms=0,
    )


def publish_custom_metric(user_id: str, value: float) -> None:
    resource_id = os.environ.get("AZURE_MONITOR_RESOURCE_ID")
    if not resource_id:
        logging.warning(
            "AZURE_MONITOR_RESOURCE_ID not set; skipping custom metric publish for %s",
            user_id,
        )
        return

    region = os.environ.get("AZURE_MONITOR_REGION", "eastus")
    credential = DefaultAzureCredential()
    token = credential.get_token("https://monitor.azure.com/.default").token
    url = f"https://{region}.monitoring.azure.com{resource_id}/metrics"
    body = {
        "time": datetime.now(timezone.utc).isoformat(),
        "data": {
            "baseData": {
                "metric": "prompt_governance_usage_anomaly",
                "namespace": "PromptGovernance",
                "dimNames": ["user_id"],
                "series": [
                    {"dimValues": [user_id], "min": value, "max": value, "sum": value, "count": 1}
                ],
            }
        },
    }
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=5,
    )
    response.raise_for_status()


def main(timer: func.TimerRequest) -> None:
    workspace_id = os.environ["AZURE_LOG_ANALYTICS_WORKSPACE_ID"]
    totals = get_active_users_24h(get_logs_client(), workspace_id)
    baselines = load_baselines()

    for user_id, today_total in totals.items():
        baseline = baselines.get(user_id, 0.0)
        if is_anomalous(today_total, baseline):
            logging.warning(
                "anomaly detected for user %s: %d tokens vs baseline %.1f",
                user_id, today_total, baseline,
            )
            event = build_anomaly_event(user_id, today_total, baseline)
            publish_to_event_hub(event)
            publish_custom_metric(user_id, float(today_total))
        baselines[user_id] = update_rolling_baseline(baseline, today_total)

    save_baselines(baselines)
