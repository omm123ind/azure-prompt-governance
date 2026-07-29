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


def build_adaptive_card(event: dict) -> dict:
    facts = [
        {"title": "Event ID", "value": str(event.get("event_id", ""))},
        {"title": "User", "value": str(event.get("user_id", ""))},
        {"title": "Action", "value": str(event.get("action_taken", ""))},
        {"title": "Reason", "value": str(event.get("block_reason") or "n/a")},
    ]
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.4",
                    "body": [
                        {"type": "TextBlock", "text": "Prompt Governance Alert", "weight": "bolder", "size": "medium"},
                        {"type": "FactSet", "facts": facts},
                    ],
                },
            }
        ],
    }
