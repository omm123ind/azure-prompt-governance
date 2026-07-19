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


def _seed_azurite_custom_rules(rules: list[dict]):
    conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    service = BlobServiceClient.from_connection_string(conn_str)
    container = service.get_container_client(os.environ["POLICY_BLOB_CONTAINER"])
    try:
        container.create_container()
    except Exception:
        pass
    container.upload_blob(
        os.environ["POLICY_BLOB_NAME"],
        json.dumps({"version": "test", "updated_at": "2026-07-19T00:00:00Z", "rules": rules}),
        overwrite=True,
    )


def test_evaluate_is_condition_scoped_not_threshold_sorted():
    # Regression test for the review finding: evaluate() must not sort rules
    # by raw numeric `threshold` across different `condition` types, since
    # those thresholds have unrelated scales (e.g. pii_confidence is 0-1,
    # max_harm_score is 0-10). Two block rules are seeded, listed in
    # rules.json in the order [block_pii_first, block_harm_second], but with
    # block_harm_second having the numerically larger raw threshold (6 > 0.8).
    #
    # The old sort-by-threshold-descending code would evaluate
    # block_harm_second first (6 sorts above 0.8) and return it as the
    # triggered_rule with notify=False, even though block_pii_first appears
    # first in rules.json and also matches. The fixed two-pass,
    # condition-scoped evaluate() must honor rules.json order among block
    # rules and pick block_pii_first, with notify=True.
    rules = [
        {
            "id": "block_pii_first",
            "description": "Block high-confidence PII (listed first, low raw threshold)",
            "condition": "pii_confidence",
            "threshold": 0.8,
            "action": "block",
            "notify": True,
            "enabled": True,
        },
        {
            "id": "block_harm_second",
            "description": "Block severe harm (listed second, high raw threshold)",
            "condition": "max_harm_score",
            "threshold": 6,
            "action": "block",
            "notify": False,
            "enabled": True,
        },
    ]
    _seed_azurite_custom_rules(rules)
    _reset_cache_for_tests()

    result = evaluate({"pii_confidence": 0.9, "jailbreak_score": 0.0, "max_harm_score": 7})

    assert result["action"] == "block"
    assert result["triggered_rule"] == "block_pii_first"
    assert result["notify"] is True
