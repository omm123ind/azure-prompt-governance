import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from azure.monitor.query import LogsQueryClient
from azure.identity import AzureCliCredential

from log_writer.function import build_audit_event
from log_ingest_consumer.function import push_to_log_analytics


def test_pushed_event_appears_in_log_analytics():
    event = build_audit_event(
        prompt="test canonical prompt for week 1 pipeline check",
        response="test response",
        classification={
            "pii_detected": False, "pii_confidence": 0.0, "pii_categories": [],
            "jailbreak_score": 0.0, "harm_hate_score": 0, "harm_violence_score": 0,
            "harm_selfharm_score": 0, "harm_sexual_score": 0,
            "classification_latency_ms": 1,
        },
        action="pass",
        model="gpt-4o-mini",
        prompt_tokens=10,
        completion_tokens=5,
        latency_ms=50,
    )

    push_to_log_analytics(event.model_dump())

    time.sleep(180)  # Log Analytics ingestion lag, even via direct API push

    credential = AzureCliCredential()
    logs_client = LogsQueryClient(credential)
    workspace_id = os.environ["AZURE_LOG_ANALYTICS_WORKSPACE_ID"]
    query = f"PromptAuditLog_CL | where event_id_s == '{event.event_id}' | take 1"
    response = logs_client.query_workspace(workspace_id, query, timespan=None)
    assert len(response.tables[0].rows) == 1
