import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.user_stats import build_team_spend_query, build_user_spend_query, main


class FakeHttpRequest:
    def __init__(self, params: dict):
        self.params = params


def test_build_user_spend_query_has_top_n_and_lookback():
    query = build_user_spend_query(lookback_days=7, top_n=20)
    assert "let lookback = 7d;" in query
    assert "top 20 by TotalCostUsd desc" in query
    assert "user_id_s" in query


def test_build_team_spend_query_has_lookback():
    query = build_team_spend_query(lookback_days=7)
    assert "let lookback = 7d;" in query
    assert "team_id_s" in query


def test_main_rejects_invalid_scope():
    req = FakeHttpRequest({"scope": "not-a-real-scope"})
    response = main(req)
    assert response.status_code == 400


def test_main_returns_user_scope_rows(monkeypatch):
    import api.user_stats as user_stats_module

    monkeypatch.setenv("AZURE_LOG_ANALYTICS_WORKSPACE_ID", "fake-workspace-id")
    monkeypatch.setattr(user_stats_module, "get_logs_client", lambda: "fake-client")
    monkeypatch.setattr(
        user_stats_module,
        "run_query",
        lambda client, workspace_id, query: [{"user_id_s": "hashed-user-1", "TotalCostUsd": 1.23}],
    )

    req = FakeHttpRequest({"scope": "user"})
    response = main(req)
    body = json.loads(response.get_body())
    assert body["scope"] == "user"
    assert body["results"][0]["user_id_s"] == "hashed-user-1"


def test_main_returns_team_scope_rows(monkeypatch):
    import api.user_stats as user_stats_module

    monkeypatch.setenv("AZURE_LOG_ANALYTICS_WORKSPACE_ID", "fake-workspace-id")
    monkeypatch.setattr(user_stats_module, "get_logs_client", lambda: "fake-client")
    monkeypatch.setattr(
        user_stats_module,
        "run_query",
        lambda client, workspace_id, query: [{"team_id_s": "hashed-team-1", "TotalCostUsd": 4.56}],
    )

    req = FakeHttpRequest({"scope": "team"})
    response = main(req)
    body = json.loads(response.get_body())
    assert body["scope"] == "team"
    assert body["results"][0]["team_id_s"] == "hashed-team-1"
