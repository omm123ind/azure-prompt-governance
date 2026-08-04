import hashlib
import json
import logging
import os
import uuid

import azure.functions as func
from azure.eventhub import EventData, EventHubProducerClient

from shared.models import AuditEvent
from alerting.discord_card import should_alert
from alerting.event_grid_publisher import publish_event as publish_alert_event

EVENT_HUB_NAME = "eh-audit-events"


def publish_to_event_hub(event: AuditEvent) -> None:
    """Publish the audit event onto Event Hub for the log_ingest_consumer.

    No-ops with a warning if AZURE_EVENT_HUB_CONNECTION_STRING is not set,
    so local/test usage that doesn't need Event Hub doesn't crash.
    """
    conn_str = os.environ.get("AZURE_EVENT_HUB_CONNECTION_STRING")
    if not conn_str:
        logging.warning(
            "AZURE_EVENT_HUB_CONNECTION_STRING not set; skipping Event Hub publish for %s",
            event.event_id,
        )
        return

    producer = EventHubProducerClient.from_connection_string(
        conn_str, eventhub_name=EVENT_HUB_NAME
    )
    with producer:
        batch = producer.create_batch()
        batch.add(EventData(event.model_dump_json()))
        producer.send_batch(batch)


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_audit_event(
    prompt: str,
    response: str,
    classification: dict,
    action: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    user_id: str = "anonymous",
    team_id: str = "unassigned",
    block_reason: str | None = None,
) -> AuditEvent:
    cost_usd = (prompt_tokens * 0.00000015) + (completion_tokens * 0.0000006)
    return AuditEvent(
        event_id=str(uuid.uuid4()),
        session_id=str(uuid.uuid4()),
        user_id=user_id,
        team_id=team_id,
        prompt_hash=hash_text(prompt),
        response_hash=hash_text(response),
        pii_detected=classification["pii_detected"],
        pii_confidence=classification["pii_confidence"],
        pii_categories=classification["pii_categories"],
        jailbreak_score=classification["jailbreak_score"],
        harm_hate_score=classification["harm_hate_score"],
        harm_violence_score=classification["harm_violence_score"],
        harm_selfharm_score=classification["harm_selfharm_score"],
        harm_sexual_score=classification["harm_sexual_score"],
        action_taken=action,
        block_reason=block_reason,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        model=model,
        latency_ms=latency_ms,
    )


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "invalid JSON body"}),
            status_code=400,
            mimetype="application/json",
        )

    event = build_audit_event(
        prompt=body.get("prompt", ""),
        response=body.get("response", ""),
        classification=body["classification"],
        action=body.get("action", "pass"),
        model=body.get("model", "gpt-4o-mini"),
        prompt_tokens=body.get("prompt_tokens", 0),
        completion_tokens=body.get("completion_tokens", 0),
        latency_ms=body.get("latency_ms", 0),
        block_reason=body.get("triggered_rule"),
    )
    logging.info("audit event built: %s", event.event_id)
    publish_to_event_hub(event)

    try:
        event_dict = event.model_dump()
        if should_alert(event_dict):
            publish_alert_event(event_dict)
    except Exception:
        logging.warning("alert publish failed for event %s", event.event_id, exc_info=True)

    return func.HttpResponse(
        json.dumps({"received": True, "event_id": event.event_id}),
        status_code=200,
        mimetype="application/json",
    )
