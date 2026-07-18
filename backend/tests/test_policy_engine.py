import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")
os.environ.setdefault("POLICY_BLOB_CONTAINER", "governance-policies-test")
os.environ.setdefault("POLICY_BLOB_NAME", "rules.json")

from azure.storage.blob import BlobServiceClient
from policy_engine.engine import get_rules, evaluate, _reset_cache_for_tests


def _seed_azurite():
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


def test_get_rules_loads_five_default_rules():
    _seed_azurite()
    _reset_cache_for_tests()
    rules = get_rules()
    assert len(rules) == 5
    assert {r["id"] for r in rules} == {
        "block_pii", "flag_jailbreak", "block_jailbreak_high",
        "flag_harm", "block_harm_high",
    }


def test_evaluate_blocks_high_confidence_pii():
    _seed_azurite()
    _reset_cache_for_tests()
    result = evaluate({"pii_confidence": 0.95, "jailbreak_score": 0.0, "max_harm_score": 0})
    assert result["action"] == "block"
    assert result["triggered_rule"] == "block_pii"


def test_evaluate_passes_clean_prompt():
    _reset_cache_for_tests()
    result = evaluate({"pii_confidence": 0.0, "jailbreak_score": 0.0, "max_harm_score": 0})
    assert result["action"] == "pass"
    assert result["triggered_rule"] is None
