import logging
import os

import azure.functions as func
import requests

from alerting.teams_card import build_adaptive_card


def post_to_teams(event_dict: dict) -> None:
    webhook_url = os.environ.get("TEAMS_WEBHOOK_URL")
    if not webhook_url:
        logging.warning(
            "TEAMS_WEBHOOK_URL not set; skipping Teams notification for %s",
            event_dict.get("event_id"),
        )
        return

    card = build_adaptive_card(event_dict)
    response = requests.post(webhook_url, json=card, timeout=5)
    response.raise_for_status()


def main(event: func.EventGridEvent) -> None:
    event_dict = event.get_json()
    logging.info("posting Teams alert for event %s", event_dict.get("event_id"))
    post_to_teams(event_dict)
