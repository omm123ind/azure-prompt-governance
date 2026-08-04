import logging
import os

import azure.functions as func
import requests

from alerting.discord_card import build_discord_message


def post_to_discord(event_dict: dict) -> None:
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logging.warning(
            "DISCORD_WEBHOOK_URL not set; skipping Discord notification for %s",
            event_dict.get("event_id"),
        )
        return

    message = build_discord_message(event_dict)
    response = requests.post(webhook_url, json=message, timeout=5)
    response.raise_for_status()


def main(event: func.EventGridEvent) -> None:
    event_dict = event.get_json()
    logging.info("posting Discord alert for event %s", event_dict.get("event_id"))
    post_to_discord(event_dict)
