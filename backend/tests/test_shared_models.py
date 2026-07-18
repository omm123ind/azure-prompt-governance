import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.models import AuditEvent, ClassificationResult


def test_audit_event_requires_hash_not_raw_prompt():
    event = AuditEvent(
        event_id="11111111-1111-1111-1111-111111111111",
        session_id="22222222-2222-2222-2222-222222222222",
        user_id="hashed-user",
        team_id="hashed-team",
        prompt_hash="a" * 64,
        response_hash="b" * 64,
        pii_detected=False,
        pii_confidence=0.0,
        pii_categories=[],
        jailbreak_score=0.0,
        harm_hate_score=0,
        harm_violence_score=0,
        harm_selfharm_score=0,
        harm_sexual_score=0,
        action_taken="pass",
        block_reason=None,
        prompt_tokens=10,
        completion_tokens=5,
        cost_usd=0.0000021,
        model="gpt-4o-mini",
        latency_ms=87,
    )
    assert not hasattr(event, "prompt")
    assert not hasattr(event, "response")
    assert event.prompt_hash == "a" * 64


def test_classification_result_defaults():
    result = ClassificationResult(
        pii_detected=False,
        pii_confidence=0.0,
        pii_categories=[],
        jailbreak_score=0.0,
        harm_hate_score=0,
        harm_violence_score=0,
        harm_selfharm_score=0,
        harm_sexual_score=0,
        classification_latency_ms=0,
    )
    assert result.pii_categories == []
