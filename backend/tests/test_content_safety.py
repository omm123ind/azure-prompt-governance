import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from classification.content_safety import analyze_content_safety

requires_content_safety = pytest.mark.skipif(
    not (os.environ.get("AZURE_CONTENT_SAFETY_ENDPOINT") and os.environ.get("AZURE_CONTENT_SAFETY_KEY")),
    reason="AZURE_CONTENT_SAFETY_ENDPOINT/KEY not set — skipping live Content Safety test",
)


@requires_content_safety
def test_analyze_content_safety_clean_prompt_scores_zero():
    result = analyze_content_safety("What is the capital of France?")
    assert result["harm_hate_score"] == 0
    assert result["harm_violence_score"] == 0
    assert result["harm_selfharm_score"] == 0
    assert result["harm_sexual_score"] == 0


@requires_content_safety
def test_analyze_content_safety_returns_expected_shape():
    result = analyze_content_safety("Tell me about the history of Rome.")
    assert set(result.keys()) == {
        "harm_hate_score", "harm_violence_score", "harm_selfharm_score", "harm_sexual_score",
    }
    for value in result.values():
        assert isinstance(value, int)
        assert 0 <= value <= 7


def test_analyze_content_safety_handles_api_error_gracefully(monkeypatch):
    class FakeClient:
        def analyze_text(self, request):
            raise RuntimeError("simulated API failure")

    import classification.content_safety as content_safety_module
    monkeypatch.setattr(content_safety_module, "_get_content_safety_client", lambda: FakeClient())

    result = analyze_content_safety("anything")
    assert result == {
        "harm_hate_score": 0,
        "harm_violence_score": 0,
        "harm_selfharm_score": 0,
        "harm_sexual_score": 0,
    }
