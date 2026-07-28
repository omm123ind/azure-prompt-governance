import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")
os.environ.setdefault("ANOMALY_BASELINE_CONTAINER", "governance-policies-test-anomaly")
os.environ.setdefault("ANOMALY_BASELINE_BLOB", "usage-baselines.json")

from azure.storage.blob import BlobServiceClient

import anomaly_checker.function as anomaly_function


def _clean_container():
    conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    service = BlobServiceClient.from_connection_string(conn_str)
    container = service.get_container_client(os.environ["ANOMALY_BASELINE_CONTAINER"])
    try:
        container.create_container()
    except Exception:
        pass
    try:
        container.get_blob_client(os.environ["ANOMALY_BASELINE_BLOB"]).delete_blob()
    except Exception:
        pass


def test_update_rolling_baseline_first_observation_seeds_baseline():
    assert anomaly_function.update_rolling_baseline(0.0, 1000) == 1000.0


def test_update_rolling_baseline_applies_hourly_decay_for_7_day_window():
    decay = 1 / (7 * 24)
    result = anomaly_function.update_rolling_baseline(700.0, 1400)
    assert round(result, 4) == round((700.0 * (1 - decay)) + (1400 * decay), 4)


class _FakeTable:
    def __init__(self, columns, rows):
        self.columns = columns
        self.rows = rows


class _FakeResponse:
    def __init__(self, table):
        self.tables = [table]


class _FakeLogsQueryClient:
    """Fake LogsQueryClient that records the query string and returns a fixed table.

    get_active_users_24h's exclusion of anomaly rows happens in the KQL query itself
    (a server-side `where` clause), not in Python post-processing, so this test
    environment (no live Log Analytics workspace) cannot exercise the actual filtering
    behavior. Instead, following the pattern used in test_kql_queries.py and
    test_audit_log_api.py's test_build_audit_search_query_includes_all_valid_filters,
    we assert the query string itself contains the required filter clause.
    """

    def __init__(self, table):
        self._table = table
        self.last_query = None

    def query_workspace(self, workspace_id, query, timespan=None):
        self.last_query = query
        return _FakeResponse(self._table)


def test_get_active_users_24h_query_excludes_anomaly_rows():
    # Table as if the server-side filter were absent: mixes a normal usage row with a
    # synthetic anomaly row. If the query lacked the exclusion clause, a live workspace
    # would have already summed the anomaly row's tokens into TotalTokens; here we can
    # only assert the query text carries the clause that prevents that on a real backend.
    table = _FakeTable(
        columns=["user_id_s", "TotalTokens"],
        rows=[["hashed-user-1", 1000]],
    )
    fake_client = _FakeLogsQueryClient(table)

    result = anomaly_function.get_active_users_24h(fake_client, "fake-workspace-id")

    assert 'action_taken_s != "anomaly"' in fake_client.last_query
    assert result == {"hashed-user-1": 1000}


def test_is_anomalous_flags_usage_over_3x_baseline():
    assert anomaly_function.is_anomalous(3001, 1000.0) is True
    assert anomaly_function.is_anomalous(3000, 1000.0) is False
    assert anomaly_function.is_anomalous(100, 0.0) is False


def test_build_anomaly_event_never_stores_raw_text():
    event = anomaly_function.build_anomaly_event("hashed-user-1", 5000, 1000.0)
    assert event.action_taken == "anomaly"
    assert event.user_id == "hashed-user-1"
    assert "5000" in event.block_reason
    assert len(event.prompt_hash) == 64


def test_load_baselines_returns_empty_dict_when_blob_missing():
    _clean_container()
    result = anomaly_function.load_baselines()
    assert result == {}


def test_load_and_save_baselines_round_trip():
    _clean_container()
    anomaly_function.save_baselines({"hashed-user-1": 1234.5})
    result = anomaly_function.load_baselines()
    assert result == {"hashed-user-1": 1234.5}


def test_main_publishes_event_hub_and_updates_baseline_on_anomaly(monkeypatch):
    _clean_container()
    anomaly_function.save_baselines({"hashed-user-1": 1000.0})

    monkeypatch.setattr(
        anomaly_function, "get_active_users_24h",
        lambda logs_client, workspace_id: {"hashed-user-1": 5000},
    )
    monkeypatch.setenv("AZURE_LOG_ANALYTICS_WORKSPACE_ID", "fake-workspace-id")

    published = []
    monkeypatch.setattr(anomaly_function, "publish_to_event_hub", lambda event: published.append(event))
    monkeypatch.setattr(anomaly_function, "publish_custom_metric", lambda user_id, value: None)

    anomaly_function.main(timer=None)

    assert len(published) == 1
    assert published[0].user_id == "hashed-user-1"
    assert published[0].action_taken == "anomaly"

    updated_baselines = anomaly_function.load_baselines()
    assert updated_baselines["hashed-user-1"] > 1000.0


def test_publish_custom_metric_skips_when_resource_id_not_set(monkeypatch):
    monkeypatch.delenv("AZURE_MONITOR_RESOURCE_ID", raising=False)
    anomaly_function.publish_custom_metric("hashed-user-1", 5000.0)
