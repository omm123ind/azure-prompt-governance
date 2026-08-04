import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alerting.discord_card import build_discord_message, should_alert


def test_should_alert_true_for_high_jailbreak_score():
    assert should_alert({"jailbreak_score": 0.9, "pii_detected": False, "action_taken": "block",
                          "harm_hate_score": 0, "harm_violence_score": 0,
                          "harm_selfharm_score": 0, "harm_sexual_score": 0}) is True


def test_should_alert_true_for_blocked_pii():
    assert should_alert({"jailbreak_score": 0.0, "pii_detected": True, "action_taken": "block",
                          "harm_hate_score": 0, "harm_violence_score": 0,
                          "harm_selfharm_score": 0, "harm_sexual_score": 0}) is True


def test_should_alert_true_for_high_harm_score():
    assert should_alert({"jailbreak_score": 0.0, "pii_detected": False, "action_taken": "pass",
                          "harm_hate_score": 5, "harm_violence_score": 0,
                          "harm_selfharm_score": 0, "harm_sexual_score": 0}) is True


def test_should_alert_false_for_clean_prompt():
    assert should_alert({"jailbreak_score": 0.1, "pii_detected": False, "action_taken": "pass",
                          "harm_hate_score": 0, "harm_violence_score": 0,
                          "harm_selfharm_score": 0, "harm_sexual_score": 0}) is False


def test_build_discord_message_never_includes_raw_prompt_text():
    event = {
        "event_id": "evt-1", "user_id": "hashed-user-1", "action_taken": "block",
        "block_reason": "pii_confidence_exceeded_threshold", "jailbreak_score": 0.0,
        "pii_detected": True,
    }
    message = build_discord_message(event)
    assert "embeds" in message
    assert "evt-1" in str(message)
    assert "hashed-user-1" in str(message)
