import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from classification.function import classify


def test_stub_always_passes():
    result = classify("Summarise the key trends in renewable energy for 2025.")
    assert result["action"] == "pass"
    assert result["triggered_rule"] is None
    assert result["classification"]["pii_detected"] is False
    assert result["classification"]["jailbreak_score"] == 0.0
