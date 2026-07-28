import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")
os.environ.setdefault("POLICY_BLOB_CONTAINER", "governance-policies-test-classification")
os.environ.setdefault("POLICY_BLOB_NAME", "rules.json")

from azure.storage.blob import BlobServiceClient

from classification.function import main
from policy_engine.engine import _reset_cache_for_tests


class FakeHttpRequest:
    def __init__(self, body: dict):
        self._body = body

    def get_json(self):
        return self._body


def _seed_azurite_rules():
    conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    service = BlobServiceClient.from_connection_string(conn_str)
    container = service.get_container_client(os.environ["POLICY_BLOB_CONTAINER"])
    try:
        container.create_container()
    except Exception:
        pass
    rules_path = Path(__file__).resolve().parents[1] / "policy_engine" / "rules.json"
    container.upload_blob(
        os.environ["POLICY_BLOB_NAME"],
        rules_path.read_text(),
        overwrite=True,
    )


def test_main_blocks_when_pii_detected(monkeypatch):
    _seed_azurite_rules()
    _reset_cache_for_tests()

    def fake_classify(prompt_text):
        return {
            "classification": {
                "pii_detected": True, "pii_confidence": 0.95, "pii_categories": ["email"],
                "jailbreak_score": 0.0, "harm_hate_score": 0, "harm_violence_score": 0,
                "harm_selfharm_score": 0, "harm_sexual_score": 0,
                "classification_latency_ms": 50,
            },
            "max_harm_score": 0,
        }

    import classification.function as classification_function
    monkeypatch.setattr(classification_function, "classify", fake_classify)

    req = FakeHttpRequest({"prompt": "my email is test@example.com"})
    response = main(req)
    body = json.loads(response.get_body())

    assert body["action"] == "block"
    assert body["triggered_rule"] == "block_pii"
    assert body["classification"]["pii_detected"] is True


def test_main_passes_clean_prompt(monkeypatch):
    _seed_azurite_rules()
    _reset_cache_for_tests()

    def fake_classify(prompt_text):
        return {
            "classification": {
                "pii_detected": False, "pii_confidence": 0.0, "pii_categories": [],
                "jailbreak_score": 0.0, "harm_hate_score": 0, "harm_violence_score": 0,
                "harm_selfharm_score": 0, "harm_sexual_score": 0,
                "classification_latency_ms": 50,
            },
            "max_harm_score": 0,
        }

    import classification.function as classification_function
    monkeypatch.setattr(classification_function, "classify", fake_classify)

    req = FakeHttpRequest({"prompt": "What is the capital of France?"})
    response = main(req)
    body = json.loads(response.get_body())

    assert body["action"] == "pass"
    assert body["triggered_rule"] is None
