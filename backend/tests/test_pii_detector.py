import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from classification.pii_detector import detect_pii

requires_openai_key = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set — skipping live classifier accuracy test",
)

LABELED_PROMPTS = [
    ("What is the capital of France?", False, []),
    ("Summarise this quarterly report for me.", False, []),
    ("Can you help me write a poem about the ocean?", False, []),
    ("What's a good recipe for banana bread?", False, []),
    ("Explain how photosynthesis works.", False, []),
    ("My email is john.smith@example.com, please reply there.", True, ["email"]),
    ("Call me on 9876543210 when you get a chance.", True, ["phone"]),
    ("My SSN is 123-45-6789, is that enough for verification?", True, ["ssn"]),
    ("Here's my Aadhaar number: 1234 5678 9012.", True, ["aadhaar"]),
    ("My PAN is ABCDE1234F for the tax filing.", True, ["pan"]),
    ("Ship it to 42 Baker Street, London, NW1 6XE.", True, ["address"]),
    ("Charge my card 4111-1111-1111-1111 for the order.", True, ["credit_card"]),
    ("My date of birth is 14th March 1990.", True, ["date_of_birth"]),
    ("Connect from IP address 192.168.1.42 please.", True, ["ip_address"]),
    ("My bank account number is 000123456789 for the refund.", True, ["bank_account"]),
    ("My passport number is L1234567, needed for the booking.", True, ["passport"]),
    ("The password for the shared drive is Summer2024!.", True, ["password"]),
    ("His name is Rajesh Kumar and he lives in Pune.", True, ["name"]),
    ("What's the weather like in Tokyo tomorrow?", False, []),
    ("Draft an email to the whole team about the new policy.", False, []),
]


@requires_openai_key
def test_pii_detector_accuracy_at_least_95_percent():
    correct = 0
    for prompt_text, expected_detected, _expected_categories in LABELED_PROMPTS:
        result = detect_pii(prompt_text)
        if result["pii_detected"] == expected_detected:
            correct += 1
    accuracy = correct / len(LABELED_PROMPTS)
    assert accuracy >= 0.95, f"PII detector accuracy {accuracy:.2%} below 95% target"


@requires_openai_key
def test_pii_detector_returns_expected_shape():
    result = detect_pii("My email is test@example.com")
    assert isinstance(result["pii_detected"], bool)
    assert isinstance(result["confidence"], float)
    assert isinstance(result["categories_found"], list)


def test_pii_detector_handles_malformed_json_gracefully(monkeypatch):
    class FakeMessage:
        content = "```json\nnot valid json at all\n```"

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    import classification.pii_detector as pii_detector_module
    monkeypatch.setattr(pii_detector_module, "get_openai_client", lambda: FakeClient())

    result = detect_pii("anything")
    assert result == {"pii_detected": False, "confidence": 0.0, "categories_found": []}


def test_pii_detector_handles_non_numeric_confidence_gracefully(monkeypatch):
    class FakeMessage:
        content = '{"pii_detected": true, "confidence": "high", "categories_found": ["email"]}'

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    import classification.pii_detector as pii_detector_module
    monkeypatch.setattr(pii_detector_module, "get_openai_client", lambda: FakeClient())

    result = detect_pii("anything")
    assert result == {"pii_detected": False, "confidence": 0.0, "categories_found": []}


def test_pii_detector_handles_none_content_gracefully(monkeypatch):
    class FakeMessage:
        content = None

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    import classification.pii_detector as pii_detector_module
    monkeypatch.setattr(pii_detector_module, "get_openai_client", lambda: FakeClient())

    result = detect_pii("anything")
    assert result == {"pii_detected": False, "confidence": 0.0, "categories_found": []}
