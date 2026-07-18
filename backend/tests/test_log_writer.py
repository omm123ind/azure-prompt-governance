import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from log_writer.function import build_audit_event, hash_text


def test_hash_text_is_sha256_hex():
    digest = hash_text("hello world")
    assert len(digest) == 64
    assert digest == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"


def test_build_audit_event_never_stores_raw_text():
    classification = {
        "pii_detected": False,
        "pii_confidence": 0.0,
        "pii_categories": [],
        "jailbreak_score": 0.0,
        "harm_hate_score": 0,
        "harm_violence_score": 0,
        "harm_selfharm_score": 0,
        "harm_sexual_score": 0,
        "classification_latency_ms": 5,
    }
    event = build_audit_event(
        prompt="my email is john@example.com",
        response="I can't help with that.",
        classification=classification,
        action="pass",
        model="gpt-4o-mini",
        prompt_tokens=12,
        completion_tokens=6,
        latency_ms=90,
    )
    dumped = event.model_dump()
    assert "prompt" not in dumped
    assert "response" not in dumped
    assert "john@example.com" not in str(dumped)
    assert len(event.prompt_hash) == 64
    assert len(event.response_hash) == 64
