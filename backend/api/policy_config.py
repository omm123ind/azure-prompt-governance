import json
import os

import azure.functions as func
from azure.storage.blob import BlobServiceClient

REQUIRED_RULE_FIELDS = {"id", "description", "condition", "threshold", "action", "notify", "enabled"}
VALID_ACTIONS = {"block", "flag", "pass"}


def _blob_client():
    conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container_name = os.environ.get("POLICY_BLOB_CONTAINER", "governance-policies")
    blob_name = os.environ.get("POLICY_BLOB_NAME", "rules.json")
    service = BlobServiceClient.from_connection_string(conn_str)
    return service.get_container_client(container_name).get_blob_client(blob_name)


def get_rules_from_blob() -> dict:
    blob = _blob_client()
    return json.loads(blob.download_blob().readall())


def _validate_rules(payload: dict) -> None:
    if "rules" not in payload or not isinstance(payload["rules"], list):
        raise ValueError("payload must have a 'rules' list")
    for rule in payload["rules"]:
        missing = REQUIRED_RULE_FIELDS - set(rule.keys())
        if missing:
            raise ValueError(f"rule {rule.get('id', '<unknown>')} missing fields: {sorted(missing)}")
        if rule["action"] not in VALID_ACTIONS:
            raise ValueError(f"rule {rule['id']} has invalid action: {rule['action']}")
        if not isinstance(rule["threshold"], (int, float)):
            raise ValueError(f"rule {rule['id']} threshold must be numeric")


def save_rules_to_blob(rules: dict) -> None:
    _validate_rules(rules)
    blob = _blob_client()
    blob.upload_blob(json.dumps(rules), overwrite=True)

    from policy_engine.engine import _reset_cache_for_tests
    _reset_cache_for_tests()


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "GET":
        rules = get_rules_from_blob()
        return func.HttpResponse(json.dumps(rules), status_code=200, mimetype="application/json")

    if req.method == "PUT":
        try:
            payload = req.get_json()
            save_rules_to_blob(payload)
        except ValueError as exc:
            return func.HttpResponse(
                json.dumps({"error": str(exc)}), status_code=400, mimetype="application/json"
            )
        return func.HttpResponse(json.dumps({"saved": True}), status_code=200, mimetype="application/json")

    return func.HttpResponse(
        json.dumps({"error": f"method {req.method} not allowed"}),
        status_code=405,
        mimetype="application/json",
    )
