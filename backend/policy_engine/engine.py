import json
import os
import threading
import time

from azure.storage.blob import BlobServiceClient

_rules_cache = None
_cache_loaded_at = 0.0
_cache_lock = threading.Lock()
CACHE_TTL = 60


def _reset_cache_for_tests():
    global _rules_cache, _cache_loaded_at
    _rules_cache = None
    _cache_loaded_at = 0.0


def load_rules_from_blob() -> list[dict]:
    conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container_name = os.environ.get("POLICY_BLOB_CONTAINER", "governance-policies")
    blob_name = os.environ.get("POLICY_BLOB_NAME", "rules.json")

    service = BlobServiceClient.from_connection_string(conn_str)
    blob = service.get_container_client(container_name).get_blob_client(blob_name)
    data = json.loads(blob.download_blob().readall())
    return data["rules"]


def get_rules() -> list[dict]:
    global _rules_cache, _cache_loaded_at
    if _rules_cache is None or (time.time() - _cache_loaded_at) > CACHE_TTL:
        with _cache_lock:
            if _rules_cache is None or (time.time() - _cache_loaded_at) > CACHE_TTL:
                _rules_cache = load_rules_from_blob()
                _cache_loaded_at = time.time()
    return _rules_cache


def get_score_for_condition(classification_result: dict, condition: str) -> float:
    return classification_result.get(condition, 0)


def evaluate(classification_result: dict) -> dict:
    rules = get_rules()
    action = "pass"
    triggered_rule = None
    should_notify = False
    for rule in sorted(rules, key=lambda r: r["threshold"], reverse=True):
        if not rule["enabled"]:
            continue
        score = get_score_for_condition(classification_result, rule["condition"])
        if score >= rule["threshold"]:
            if rule["action"] == "block":
                action = "block"
                triggered_rule = rule["id"]
                should_notify = rule["notify"]
                break
            elif rule["action"] == "flag" and action != "block":
                action = "flag"
                triggered_rule = rule["id"]
                should_notify = rule["notify"]
    return {"action": action, "triggered_rule": triggered_rule, "notify": should_notify}
