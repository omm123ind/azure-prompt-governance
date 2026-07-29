import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("RBAC_TEST_MODE", "true")

import jwt
import pytest

from api.audit_log import build_audit_search_query, main

_FAKE_TOKEN = jwt.encode({"roles": ["audit-viewer"]}, "test-secret", algorithm="HS256")


class FakeHttpRequest:
    def __init__(self, params: dict, headers: dict | None = None):
        self.params = params
        self.headers = headers or {"Authorization": f"Bearer {_FAKE_TOKEN}"}


def test_build_audit_search_query_rejects_injection_in_user_id():
    with pytest.raises(ValueError):
        build_audit_search_query(
            start_time="2026-07-01T00:00:00Z",
            end_time="2026-07-02T00:00:00Z",
            user_id='abc" or true; drop table --',
        )


def test_build_audit_search_query_rejects_invalid_action():
    with pytest.raises(ValueError):
        build_audit_search_query(
            start_time="2026-07-01T00:00:00Z",
            end_time="2026-07-02T00:00:00Z",
            action="delete_everything",
        )


def test_build_audit_search_query_includes_all_valid_filters():
    query = build_audit_search_query(
        start_time="2026-07-01T00:00:00Z",
        end_time="2026-07-02T00:00:00Z",
        user_id="hashed-user-1",
        team_id="hashed-team-1",
        action="block",
        flag_type="pii",
    )
    assert 'user_id_s == "hashed-user-1"' in query
    assert 'team_id_s == "hashed-team-1"' in query
    assert 'action_taken_s == "block"' in query
    assert "pii_detected_b == true" in query


def test_main_returns_400_when_start_time_missing():
    req = FakeHttpRequest({"end_time": "2026-07-02T00:00:00Z"})
    response = main(req)
    assert response.status_code == 400


def test_main_returns_rows_from_run_query(monkeypatch):
    import api.audit_log as audit_log_module

    monkeypatch.setenv("AZURE_LOG_ANALYTICS_WORKSPACE_ID", "fake-workspace-id")
    monkeypatch.setattr(audit_log_module, "get_logs_client", lambda: "fake-client")
    monkeypatch.setattr(
        audit_log_module,
        "run_query",
        lambda client, workspace_id, query: [{"event_id_s": "abc123"}],
    )

    req = FakeHttpRequest({
        "start_time": "2026-07-01T00:00:00Z",
        "end_time": "2026-07-02T00:00:00Z",
    })
    response = main(req)
    body = json.loads(response.get_body())
    assert body["count"] == 1
    assert body["results"][0]["event_id_s"] == "abc123"
