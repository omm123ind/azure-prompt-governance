import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")
os.environ.setdefault("POLICY_BLOB_CONTAINER", "governance-policies-test-config")
os.environ.setdefault("POLICY_BLOB_NAME", "rules.json")

from azure.storage.blob import BlobServiceClient

from api.policy_config import main
from policy_engine.engine import _reset_cache_for_tests


class FakeHttpRequest:
    def __init__(self, method: str, body: dict | None = None):
        self.method = method
        self._body = body

    def get_json(self):
        if self._body is None:
            raise ValueError("no body")
        return self._body


def _seed_container():
    conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    service = BlobServiceClient.from_connection_string(conn_str)
    container = service.get_container_client(os.environ["POLICY_BLOB_CONTAINER"])
    try:
        container.create_container()
    except Exception:
        pass
    container.upload_blob(
        os.environ["POLICY_BLOB_NAME"],
        json.dumps({
            "version": "1.0",
            "updated_at": "2026-07-19T00:00:00Z",
            "rules": [
                {
                    "id": "block_pii", "description": "d", "condition": "pii_confidence",
                    "threshold": 0.8, "action": "block", "notify": True, "enabled": True,
                }
            ],
        }),
        overwrite=True,
    )


def test_get_returns_current_rules():
    _seed_container()
    _reset_cache_for_tests()
    response = main(FakeHttpRequest("GET"))
    body = json.loads(response.get_body())
    assert body["rules"][0]["id"] == "block_pii"


def test_put_saves_valid_rules_and_invalidates_cache():
    _seed_container()
    _reset_cache_for_tests()
    new_rules = {
        "version": "1.1",
        "updated_at": "2026-07-29T00:00:00Z",
        "rules": [
            {
                "id": "block_pii", "description": "updated", "condition": "pii_confidence",
                "threshold": 0.9, "action": "block", "notify": True, "enabled": True,
            }
        ],
    }
    response = main(FakeHttpRequest("PUT", body=new_rules))
    assert response.status_code == 200

    from policy_engine.engine import get_rules
    rules = get_rules()
    assert rules[0]["threshold"] == 0.9


def test_put_rejects_malformed_rules():
    _seed_container()
    _reset_cache_for_tests()
    bad_rules = {"version": "1.0", "updated_at": "now", "rules": [{"id": "missing_fields"}]}
    response = main(FakeHttpRequest("PUT", body=bad_rules))
    assert response.status_code == 400


def test_put_rejects_missing_version_and_updated_at():
    _seed_container()
    _reset_cache_for_tests()
    bad_rules = {
        "rules": [
            {
                "id": "block_pii", "description": "d", "condition": "pii_confidence",
                "threshold": 0.8, "action": "block", "notify": True, "enabled": True,
            }
        ],
    }
    response = main(FakeHttpRequest("PUT", body=bad_rules))
    assert response.status_code == 400


def test_put_rejects_empty_rules_list():
    _seed_container()
    _reset_cache_for_tests()
    bad_rules = {"version": "1.0", "updated_at": "now", "rules": []}
    response = main(FakeHttpRequest("PUT", body=bad_rules))
    assert response.status_code == 400


def test_unsupported_method_returns_405():
    response = main(FakeHttpRequest("DELETE"))
    assert response.status_code == 405
