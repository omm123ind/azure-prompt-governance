import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from classification.function import classify


def test_classify_runs_all_three_in_parallel(monkeypatch):
    call_order = []

    def fake_pii(prompt_text):
        call_order.append("pii_start")
        time.sleep(0.05)
        call_order.append("pii_end")
        return {"pii_detected": True, "confidence": 0.9, "categories_found": ["email"]}

    def fake_jailbreak(prompt_text):
        call_order.append("jailbreak_start")
        time.sleep(0.05)
        call_order.append("jailbreak_end")
        return {"jailbreak_detected": False, "confidence": 0.1, "pattern": None}

    def fake_harm(prompt_text):
        call_order.append("harm_start")
        time.sleep(0.05)
        call_order.append("harm_end")
        return {
            "harm_hate_score": 0, "harm_violence_score": 0,
            "harm_selfharm_score": 0, "harm_sexual_score": 0,
        }

    import classification.function as classification_function
    monkeypatch.setattr(classification_function, "detect_pii", fake_pii)
    monkeypatch.setattr(classification_function, "detect_jailbreak", fake_jailbreak)
    monkeypatch.setattr(classification_function, "analyze_content_safety", fake_harm)

    start = time.time()
    result = classify("test prompt")
    elapsed = time.time() - start

    # All three ran concurrently: total time is close to one 0.05s sleep,
    # not three sequential ones (which would be ~0.15s).
    assert elapsed < 0.12

    # All three "start" events happened before all three "end" events
    # if they ran sequentially — check they interleave instead.
    starts_before_first_end = call_order[:call_order.index([e for e in call_order if e.endswith("_end")][0])]
    assert len(starts_before_first_end) >= 2  # at least 2 of 3 started before any finished


def test_classify_merges_results_into_classification_result_shape(monkeypatch):
    def fake_pii(prompt_text):
        return {"pii_detected": True, "confidence": 0.9, "categories_found": ["email"]}

    def fake_jailbreak(prompt_text):
        return {"jailbreak_detected": False, "confidence": 0.05, "pattern": None}

    def fake_harm(prompt_text):
        return {
            "harm_hate_score": 2, "harm_violence_score": 5,
            "harm_selfharm_score": 0, "harm_sexual_score": 1,
        }

    import classification.function as classification_function
    monkeypatch.setattr(classification_function, "detect_pii", fake_pii)
    monkeypatch.setattr(classification_function, "detect_jailbreak", fake_jailbreak)
    monkeypatch.setattr(classification_function, "analyze_content_safety", fake_harm)

    result = classify("test prompt")

    classification = result["classification"]
    assert classification["pii_detected"] is True
    assert classification["pii_confidence"] == 0.9
    assert classification["pii_categories"] == ["email"]
    assert classification["jailbreak_score"] == 0.05
    assert classification["harm_hate_score"] == 2
    assert classification["harm_violence_score"] == 5
    assert classification["harm_selfharm_score"] == 0
    assert classification["harm_sexual_score"] == 1
    assert isinstance(classification["classification_latency_ms"], int)

    # max_harm_score is the max of the four harm scores (5, from violence)
    assert result["max_harm_score"] == 5
