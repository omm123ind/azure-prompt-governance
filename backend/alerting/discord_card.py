JAILBREAK_ALERT_THRESHOLD = 0.85
HARM_ALERT_THRESHOLD = 5


def should_alert(event: dict) -> bool:
    if event.get("jailbreak_score", 0.0) >= JAILBREAK_ALERT_THRESHOLD:
        return True
    if event.get("pii_detected", False) and event.get("action_taken") == "block":
        return True
    harm_scores = [
        event.get("harm_hate_score", 0),
        event.get("harm_violence_score", 0),
        event.get("harm_selfharm_score", 0),
        event.get("harm_sexual_score", 0),
    ]
    return max(harm_scores) >= HARM_ALERT_THRESHOLD


ALERT_COLOR = 0xE74C3C  # red


def build_discord_message(event: dict) -> dict:
    fields = [
        {"name": "Event ID", "value": str(event.get("event_id", "")), "inline": True},
        {"name": "User", "value": str(event.get("user_id", "")), "inline": True},
        {"name": "Action", "value": str(event.get("action_taken", "")), "inline": True},
        {"name": "Reason", "value": str(event.get("block_reason") or "n/a"), "inline": True},
    ]
    return {
        "embeds": [
            {
                "title": "Prompt Governance Alert",
                "color": ALERT_COLOR,
                "fields": fields,
            }
        ],
    }
