import json
import os
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from azure.eventhub import EventHubProducerClient, EventData
from azure.monitor.query import LogsQueryClient
from azure.identity import AzureCliCredential

from log_writer.function import build_audit_event


def test_published_event_appears_in_log_analytics():
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

    conn_str = os.environ["AZURE_EVENT_HUB_CONNECTION_STRING"]
    producer = EventHubProducerClient.from_connection_string(
        conn_str, eventhub_name="eh-audit-events"
    )
    with producer:
        batch = producer.create_batch()
        batch.add(EventData(event.model_dump_json()))
        producer.send_batch(batch)

    time.sleep(120)  # first ingestion can take ~10 minutes per spec Section 11 Day 4-5; CI should poll instead

    credential = AzureCliCredential()
    logs_client = LogsQueryClient(credential)
    workspace_id = os.environ["AZURE_LOG_ANALYTICS_WORKSPACE_ID"]
    query = f"PromptAuditLog_CL | where event_id_s == '{event.event_id}' | take 1"
    response = logs_client.query_workspace(workspace_id, query, timespan=None)
    assert len(response.tables[0].rows) == 1
