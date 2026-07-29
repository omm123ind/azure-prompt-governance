import logging
import os
import uuid
from datetime import datetime, timezone

import requests


def publish_event(event: dict) -> None:
    endpoint = os.environ.get("AZURE_EVENT_GRID_TOPIC_ENDPOINT")
    key = os.environ.get("AZURE_EVENT_GRID_TOPIC_KEY")
    if not endpoint or not key:
        logging.warning(
            "AZURE_EVENT_GRID_TOPIC_ENDPOINT/KEY not set; skipping Event Grid publish for %s",
            event.get("event_id"),
        )
        return

    body = [
        {
            "id": str(uuid.uuid4()),
            "eventType": "PromptGovernance.HighSeverityFlag",
            "subject": f"prompt-governance/events/{event.get('event_id')}",
            "eventTime": datetime.now(timezone.utc).isoformat(),
            "data": event,
            "dataVersion": "1.0",
        }
    ]
    response = requests.post(
        endpoint,
        headers={"aeg-sas-key": key, "Content-Type": "application/json"},
        json=body,
        timeout=5,
    )
    response.raise_for_status()
