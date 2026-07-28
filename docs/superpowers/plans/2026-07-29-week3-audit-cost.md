# Week 3 Audit Trail and Cost Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Week 3 deliverable from `CLAUDE_CODE_CONTEXT.txt` Section 11 — a full queryable audit log with token cost per user and team: the 8-query KQL library against `PromptAuditLog_CL`, an hourly anomaly-detection function comparing 24h usage to a rolling 7-day baseline, and two REST API functions (`audit_log`, `user_stats`) that the Week 4 dashboard will call.

**Architecture:** Week 1 already built `log_writer/function.py` (serialises the complete `AuditEvent`, computes `cost_usd`, publishes to Event Hub) and `log_ingest_consumer/function.py` (Event-Hub-triggered, pushes rows into `PromptAuditLog_CL` via the Logs Ingestion API) — so Day 1-3's "build the log-writer fully" and "add cost tracking" are already satisfied and this plan does not re-touch either file. What's missing and what this plan builds: the 8 KQL queries under `infrastructure/kql-queries/`, a new `backend/anomaly_checker/` Timer-triggered function (reusing `log_writer.function.publish_to_event_hub` and `shared.models.AuditEvent` to write anomaly records into the same table via the existing pipeline — DRY, no schema change), and two new `backend/api/` REST functions. Anomaly records are distinguished from normal prompt events by `action_taken="anomaly"` on the existing `action_taken_s` string column (documented in Task 2, not a silent schema change).

**Tech Stack:** Same as Week 1/2 — Python 3.11, `azure-storage-blob` (Azurite-backed for local tests), `azure-monitor-query` (`LogsQueryClient`, mocked/monkeypatched in tests — no live workspace call in the local suite), `azure-identity`, `requests` (Azure Monitor custom-metrics REST call), pytest.

## Global Constraints

- No raw prompt/response text may be persisted anywhere in this plan — every new code path only ever touches `prompt_hash`/`response_hash`/hashed `user_id`/`team_id`, consistent with `[[project-scope]]`'s privacy requirement.
- `cost_usd` formula stays exactly `(prompt_tokens * 0.00000015) + (completion_tokens * 0.0000006)` (gpt-4o-mini pricing) — already implemented in `log_writer/function.py:build_audit_event`, do not duplicate or redefine it elsewhere.
- All 8 KQL queries reference table `PromptAuditLog_CL` only, and use `let` statements for time windows (`ago(Nd)`/`ago(Nh)`) so the dashboard can pass the window as a variable, per spec Section 9.
- Anomaly threshold is exactly 3x the rolling 7-day baseline (spec Section 11, Week 3 Day 4) — this constant lives in `shared/constants.py` as `ANOMALY_MULTIPLIER = 3`, not hardcoded inline.
- Any new env var goes in `backend/local.settings.json.example` (documentation only — the real `local.settings.json` stays gitignored, never committed).
- User-supplied query filters (`user_id`, `team_id`, `action`) in the REST API functions must be validated against an allowlist/regex before being interpolated into a KQL string — never pass raw request input into a query unvalidated (KQL injection).
- Do not modify `classification/`, `policy_engine/`, `log_writer/`, or `log_ingest_consumer/` — all already correct for Week 3's needs, reused as-is.

---

### Task 1: KQL query library (all 8 queries)

**Files:**
- Create: `infrastructure/kql-queries/flag-summary.kql`
- Create: `infrastructure/kql-queries/user-spend.kql`
- Create: `infrastructure/kql-queries/team-spend.kql`
- Create: `infrastructure/kql-queries/jailbreak-heatmap.kql`
- Create: `infrastructure/kql-queries/pii-events.kql`
- Create: `infrastructure/kql-queries/harm-by-category.kql`
- Create: `infrastructure/kql-queries/anomaly-events.kql`
- Create: `infrastructure/kql-queries/audit-search.kql`
- Test: `backend/tests/test_kql_queries.py`

**Interfaces:**
- Consumes: nothing (static text files).
- Produces: the file set at `infrastructure/kql-queries/*.kql` — Task 3's `audit_log.py` builds its own dynamic query in Python (not by reading these files) but must produce KQL structurally equivalent to `audit-search.kql`'s shape; Task 4's `user_stats.py` builds queries structurally equivalent to `user-spend.kql`/`team-spend.kql`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_kql_queries.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

KQL_DIR = Path(__file__).resolve().parents[2] / "infrastructure" / "kql-queries"

EXPECTED_QUERIES = {
    "flag-summary.kql": ["PromptAuditLog_CL", "action_taken_s", "ago("],
    "user-spend.kql": ["PromptAuditLog_CL", "cost_usd_d", "user_id_s", "ago("],
    "team-spend.kql": ["PromptAuditLog_CL", "cost_usd_d", "team_id_s", "ago("],
    "jailbreak-heatmap.kql": ["PromptAuditLog_CL", "jailbreak_score_d", "hourofday", "ago("],
    "pii-events.kql": ["PromptAuditLog_CL", "pii_detected_b", "ago("],
    "harm-by-category.kql": [
        "PromptAuditLog_CL", "harm_hate_score_d", "harm_violence_score_d",
        "harm_selfharm_score_d", "harm_sexual_score_d", "ago(",
    ],
    "anomaly-events.kql": ["PromptAuditLog_CL", 'action_taken_s == "anomaly"', "ago("],
    "audit-search.kql": ["PromptAuditLog_CL", "TimeGenerated between"],
}


def test_all_eight_kql_queries_exist():
    for filename in EXPECTED_QUERIES:
        assert (KQL_DIR / filename).exists(), f"missing {filename}"


def test_each_query_references_the_correct_table_and_required_fields():
    for filename, required_substrings in EXPECTED_QUERIES.items():
        content = (KQL_DIR / filename).read_text()
        for substring in required_substrings:
            assert substring in content, f"{filename} missing expected substring: {substring}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/test_kql_queries.py -v`
Expected: FAIL — `infrastructure/kql-queries` directory does not exist yet.

- [ ] **Step 3: Write `infrastructure/kql-queries/flag-summary.kql`**

```kql
let lookback = 24h;
PromptAuditLog_CL
| where TimeGenerated > ago(lookback)
| summarize EventCount = count() by action_taken_s
| order by EventCount desc
```

- [ ] **Step 4: Write `infrastructure/kql-queries/user-spend.kql`**

```kql
let lookback = 7d;
PromptAuditLog_CL
| where TimeGenerated > ago(lookback)
| summarize
    TotalCostUsd = sum(cost_usd_d),
    TotalPromptTokens = sum(prompt_tokens_d),
    TotalCompletionTokens = sum(completion_tokens_d)
  by user_id_s
| top 20 by TotalCostUsd desc
```

- [ ] **Step 5: Write `infrastructure/kql-queries/team-spend.kql`**

```kql
let lookback = 7d;
PromptAuditLog_CL
| where TimeGenerated > ago(lookback)
| summarize TotalCostUsd = sum(cost_usd_d) by team_id_s
| order by TotalCostUsd desc
```

- [ ] **Step 6: Write `infrastructure/kql-queries/jailbreak-heatmap.kql`**

```kql
let lookback = 7d;
let jailbreakThreshold = 0.6;
PromptAuditLog_CL
| where TimeGenerated > ago(lookback)
| where jailbreak_score_d > jailbreakThreshold
| summarize AttemptCount = count() by HourOfDay = hourofday(TimeGenerated)
| order by HourOfDay asc
```

- [ ] **Step 7: Write `infrastructure/kql-queries/pii-events.kql`**

```kql
let lookback = 24h;
PromptAuditLog_CL
| where TimeGenerated > ago(lookback)
| where pii_detected_b == true
| project TimeGenerated, event_id_s, user_id_s, team_id_s, pii_categories_s, action_taken_s
| order by TimeGenerated desc
```

- [ ] **Step 8: Write `infrastructure/kql-queries/harm-by-category.kql`**

```kql
let lookback = 7d;
PromptAuditLog_CL
| where TimeGenerated > ago(lookback)
| summarize
    AvgHate = avg(harm_hate_score_d),
    AvgViolence = avg(harm_violence_score_d),
    AvgSelfHarm = avg(harm_selfharm_score_d),
    AvgSexual = avg(harm_sexual_score_d)
```

- [ ] **Step 9: Write `infrastructure/kql-queries/anomaly-events.kql`**

`PromptAuditLog_CL` has no separate event-type column — Task 2's anomaly checker reuses the existing `action_taken_s` string column with the value `"anomaly"` (alongside `"block"`/`"flag"`/`"pass"`) instead of migrating the whole table schema. This query relies on that convention:

```kql
let lookback = 7d;
PromptAuditLog_CL
| where TimeGenerated > ago(lookback)
| where action_taken_s == "anomaly"
| project TimeGenerated, event_id_s, user_id_s, team_id_s, block_reason_s
| order by TimeGenerated desc
```

- [ ] **Step 10: Write `infrastructure/kql-queries/audit-search.kql`**

This is a documentation/reference copy of the query shape `backend/api/audit_log.py` (Task 3) builds dynamically in Python (filters are runtime values, not static KQL literals, so the real query is assembled in code, not read from this file):

```kql
let startTime = datetime(2026-07-01T00:00:00Z);
let endTime = datetime(2026-07-02T00:00:00Z);
PromptAuditLog_CL
| where TimeGenerated between (startTime .. endTime)
| where user_id_s == "REPLACE_WITH_HASHED_USER_ID"
| where team_id_s == "REPLACE_WITH_HASHED_TEAM_ID"
| where action_taken_s == "REPLACE_WITH_ACTION"
| order by TimeGenerated desc
| take 50
```

- [ ] **Step 11: Run test to verify it passes**

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/test_kql_queries.py -v`
Expected: `2 passed`

- [ ] **Step 12: Commit**

```bash
git add infrastructure/kql-queries backend/tests/test_kql_queries.py
git commit -m "feat: add 8-query KQL library for PromptAuditLog_CL"
```

---

### Task 2: Anomaly checker function (Timer-triggered, hourly)

**Files:**
- Create: `backend/anomaly_checker/__init__.py`
- Create: `backend/anomaly_checker/function.py`
- Modify: `backend/shared/constants.py` (add `ANOMALY_MULTIPLIER`)
- Modify: `backend/requirements.txt` (add `requests`)
- Test: `backend/tests/test_anomaly_checker.py`

**Interfaces:**
- Consumes: `log_writer.function.publish_to_event_hub(event: AuditEvent) -> None` and `log_writer.function.hash_text(text: str) -> str` (Week 1, unchanged), `shared.models.AuditEvent` (Week 1, unchanged).
- Produces: `get_active_users_24h(logs_client, workspace_id: str) -> dict[str, int]`, `load_baselines() -> dict[str, float]`, `save_baselines(baselines: dict[str, float]) -> None`, `update_rolling_baseline(previous_baseline: float, today_total: int, decay: float = 1/7) -> float`, `is_anomalous(today_total: int, baseline: float) -> bool`, `build_anomaly_event(user_id: str, today_total: int, baseline: float) -> AuditEvent`, `publish_custom_metric(user_id: str, value: float) -> None` — Task 5 wires `main(timer)` into `function_app.py`'s timer trigger.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_anomaly_checker.py`:
```python
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


def test_update_rolling_baseline_applies_one_seventh_decay():
    result = anomaly_function.update_rolling_baseline(700.0, 1400)
    assert round(result, 2) == round((700.0 * 6 / 7) + (1400 * 1 / 7), 2)


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/test_anomaly_checker.py -v`
Expected: needs Azurite running (`npx azurite --skipApiVersionCheck ...` or `docker compose up -d azurite` if Docker is available). With Azurite up: FAILS with `ModuleNotFoundError: No module named 'anomaly_checker'`.

- [ ] **Step 3: Add `ANOMALY_MULTIPLIER` to `backend/shared/constants.py`**

Append to the existing file:
```python
ANOMALY_MULTIPLIER = 3
```

- [ ] **Step 4: Add `requests` to `backend/requirements.txt`**

Append a line: `requests>=2.31.0`

- [ ] **Step 5: Write `backend/anomaly_checker/__init__.py`** (empty)

- [ ] **Step 6: Write `backend/anomaly_checker/function.py`**

```python
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import azure.functions as func
import requests
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient
from azure.storage.blob import BlobServiceClient

from log_writer.function import hash_text, publish_to_event_hub
from shared.constants import ANOMALY_MULTIPLIER
from shared.models import AuditEvent

_logs_client = None


def get_logs_client() -> LogsQueryClient:
    global _logs_client
    if _logs_client is None:
        _logs_client = LogsQueryClient(DefaultAzureCredential())
    return _logs_client


def get_active_users_24h(logs_client: LogsQueryClient, workspace_id: str) -> dict:
    query = "\n".join([
        "PromptAuditLog_CL",
        "| where TimeGenerated > ago(24h)",
        "| summarize TotalTokens = sum(prompt_tokens_d + completion_tokens_d) by user_id_s",
    ])
    response = logs_client.query_workspace(workspace_id, query, timespan=None)
    table = response.tables[0]
    rows = [dict(zip(table.columns, row)) for row in table.rows]
    return {row["user_id_s"]: int(row["TotalTokens"]) for row in rows}


def _baseline_blob_client():
    conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container_name = os.environ.get("ANOMALY_BASELINE_CONTAINER", "governance-policies")
    blob_name = os.environ.get("ANOMALY_BASELINE_BLOB", "usage-baselines.json")
    service = BlobServiceClient.from_connection_string(conn_str)
    return service.get_container_client(container_name).get_blob_client(blob_name)


def load_baselines() -> dict:
    blob = _baseline_blob_client()
    try:
        return json.loads(blob.download_blob().readall())
    except Exception:
        return {}


def save_baselines(baselines: dict) -> None:
    blob = _baseline_blob_client()
    blob.upload_blob(json.dumps(baselines), overwrite=True)


def update_rolling_baseline(previous_baseline: float, today_total: int, decay: float = 1 / 7) -> float:
    if previous_baseline == 0:
        return float(today_total)
    return (previous_baseline * (1 - decay)) + (today_total * decay)


def is_anomalous(today_total: int, baseline: float) -> bool:
    return baseline > 0 and today_total > baseline * ANOMALY_MULTIPLIER


def build_anomaly_event(user_id: str, today_total: int, baseline: float) -> AuditEvent:
    return AuditEvent(
        event_id=str(uuid.uuid4()),
        session_id=str(uuid.uuid4()),
        user_id=user_id,
        team_id="unassigned",
        prompt_hash=hash_text(f"anomaly-check-{user_id}-{today_total}"),
        response_hash=hash_text(""),
        pii_detected=False,
        pii_confidence=0.0,
        pii_categories=[],
        jailbreak_score=0.0,
        harm_hate_score=0,
        harm_violence_score=0,
        harm_selfharm_score=0,
        harm_sexual_score=0,
        action_taken="anomaly",
        block_reason=(
            f"24h token usage {today_total} exceeded "
            f"{ANOMALY_MULTIPLIER}x baseline {baseline:.1f}"
        ),
        prompt_tokens=today_total,
        completion_tokens=0,
        cost_usd=0.0,
        model="n/a",
        latency_ms=0,
    )


def publish_custom_metric(user_id: str, value: float) -> None:
    resource_id = os.environ.get("AZURE_MONITOR_RESOURCE_ID")
    if not resource_id:
        logging.warning(
            "AZURE_MONITOR_RESOURCE_ID not set; skipping custom metric publish for %s",
            user_id,
        )
        return

    region = os.environ.get("AZURE_MONITOR_REGION", "eastus")
    credential = DefaultAzureCredential()
    token = credential.get_token("https://monitor.azure.com/.default").token
    url = f"https://{region}.monitoring.azure.com{resource_id}/metrics"
    body = {
        "time": datetime.now(timezone.utc).isoformat(),
        "data": {
            "baseData": {
                "metric": "prompt_governance_usage_anomaly",
                "namespace": "PromptGovernance",
                "dimNames": ["user_id"],
                "series": [
                    {"dimValues": [user_id], "min": value, "max": value, "sum": value, "count": 1}
                ],
            }
        },
    }
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=5,
    )
    response.raise_for_status()


def main(timer: func.TimerRequest) -> None:
    workspace_id = os.environ["AZURE_LOG_ANALYTICS_WORKSPACE_ID"]
    totals = get_active_users_24h(get_logs_client(), workspace_id)
    baselines = load_baselines()

    for user_id, today_total in totals.items():
        baseline = baselines.get(user_id, 0.0)
        if is_anomalous(today_total, baseline):
            logging.warning(
                "anomaly detected for user %s: %d tokens vs baseline %.1f",
                user_id, today_total, baseline,
            )
            event = build_anomaly_event(user_id, today_total, baseline)
            publish_to_event_hub(event)
            publish_custom_metric(user_id, float(today_total))
        baselines[user_id] = update_rolling_baseline(baseline, today_total)

    save_baselines(baselines)
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/test_anomaly_checker.py -v`
Expected: `8 passed` (requires Azurite; the Event Hub publish and Azure Monitor metric call are monkeypatched, not live).

- [ ] **Step 8: Commit**

```bash
git add backend/anomaly_checker backend/shared/constants.py backend/requirements.txt backend/tests/test_anomaly_checker.py
git commit -m "feat: add hourly anomaly checker, 3x rolling-baseline detection"
```

---

### Task 3: `audit_log` REST API (query with filters)

**Files:**
- Create: `backend/api/__init__.py`
- Create: `backend/api/audit_log.py`
- Test: `backend/tests/test_audit_log_api.py`

**Interfaces:**
- Consumes: nothing from Tasks 1-2 directly (references the same `PromptAuditLog_CL` schema).
- Produces: `build_audit_search_query(start_time, end_time, user_id="", team_id="", action="", flag_type="") -> str`, `run_query(logs_client, workspace_id, query) -> list[dict]`, `get_logs_client() -> LogsQueryClient` — Task 5 wires `main(req)` into `function_app.py` as an HTTP route.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_audit_log_api.py`:
```python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from api.audit_log import build_audit_search_query, main


class FakeHttpRequest:
    def __init__(self, params: dict):
        self.params = params


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/test_audit_log_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'api'`

- [ ] **Step 3: Write `backend/api/__init__.py`** (empty)

- [ ] **Step 4: Write `backend/api/audit_log.py`**

```python
import json
import os
import re
from datetime import datetime

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient

ALLOWED_ACTIONS = {"block", "flag", "pass", "anomaly"}
ALLOWED_FLAG_TYPES = {"pii", "jailbreak", "harm"}
ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-]{1,128}$")

_logs_client = None


def get_logs_client() -> LogsQueryClient:
    global _logs_client
    if _logs_client is None:
        _logs_client = LogsQueryClient(DefaultAzureCredential())
    return _logs_client


def _validate_id(value: str, field_name: str) -> str:
    if not ID_PATTERN.match(value):
        raise ValueError(f"invalid {field_name}: must be alphanumeric/hyphen, 1-128 chars")
    return value


def build_audit_search_query(
    start_time: str,
    end_time: str,
    user_id: str = "",
    team_id: str = "",
    action: str = "",
    flag_type: str = "",
) -> str:
    datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    datetime.fromisoformat(end_time.replace("Z", "+00:00"))

    if user_id:
        _validate_id(user_id, "user_id")
    if team_id:
        _validate_id(team_id, "team_id")
    if action and action not in ALLOWED_ACTIONS:
        raise ValueError(f"invalid action: must be one of {sorted(ALLOWED_ACTIONS)}")
    if flag_type and flag_type not in ALLOWED_FLAG_TYPES:
        raise ValueError(f"invalid flag_type: must be one of {sorted(ALLOWED_FLAG_TYPES)}")

    clauses = [
        "PromptAuditLog_CL",
        f'| where TimeGenerated between (datetime({start_time}) .. datetime({end_time}))',
    ]
    if user_id:
        clauses.append(f'| where user_id_s == "{user_id}"')
    if team_id:
        clauses.append(f'| where team_id_s == "{team_id}"')
    if action:
        clauses.append(f'| where action_taken_s == "{action}"')
    if flag_type == "pii":
        clauses.append("| where pii_detected_b == true")
    elif flag_type == "jailbreak":
        clauses.append("| where jailbreak_score_d > 0.6")
    elif flag_type == "harm":
        clauses.append(
            "| where harm_hate_score_d > 4 or harm_violence_score_d > 4 "
            "or harm_selfharm_score_d > 4 or harm_sexual_score_d > 4"
        )
    clauses.append("| order by TimeGenerated desc")
    clauses.append("| take 50")
    return "\n".join(clauses)


def run_query(logs_client: LogsQueryClient, workspace_id: str, query: str) -> list:
    response = logs_client.query_workspace(workspace_id, query, timespan=None)
    table = response.tables[0]
    return [dict(zip(table.columns, row)) for row in table.rows]


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        start_time = req.params.get("start_time")
        end_time = req.params.get("end_time")
        if not start_time or not end_time:
            raise ValueError("start_time and end_time query parameters are required")

        query = build_audit_search_query(
            start_time=start_time,
            end_time=end_time,
            user_id=req.params.get("user_id", ""),
            team_id=req.params.get("team_id", ""),
            action=req.params.get("action", ""),
            flag_type=req.params.get("flag_type", ""),
        )
    except ValueError as exc:
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            status_code=400,
            mimetype="application/json",
        )

    workspace_id = os.environ["AZURE_LOG_ANALYTICS_WORKSPACE_ID"]
    rows = run_query(get_logs_client(), workspace_id, query)
    return func.HttpResponse(
        json.dumps({"results": rows, "count": len(rows)}),
        status_code=200,
        mimetype="application/json",
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/test_audit_log_api.py -v`
Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/api/__init__.py backend/api/audit_log.py backend/tests/test_audit_log_api.py
git commit -m "feat: add audit_log REST API with validated KQL filter query"
```

---

### Task 4: `user_stats` REST API (per-user and per-team spend)

**Files:**
- Create: `backend/api/user_stats.py`
- Test: `backend/tests/test_user_stats_api.py`

**Interfaces:**
- Consumes: nothing from other tasks (parallel structure to Task 3, does not import from it).
- Produces: `build_user_spend_query(lookback_days=7, top_n=20) -> str`, `build_team_spend_query(lookback_days=7) -> str`, `run_query(logs_client, workspace_id, query) -> list[dict]`, `get_logs_client() -> LogsQueryClient` — Task 5 wires `main(req)` into `function_app.py` as an HTTP route.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_user_stats_api.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/test_user_stats_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'api.user_stats'`

- [ ] **Step 3: Write `backend/api/user_stats.py`**

```python
import json
import os

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient

_logs_client = None


def get_logs_client() -> LogsQueryClient:
    global _logs_client
    if _logs_client is None:
        _logs_client = LogsQueryClient(DefaultAzureCredential())
    return _logs_client


def build_user_spend_query(lookback_days: int = 7, top_n: int = 20) -> str:
    return "\n".join([
        f"let lookback = {lookback_days}d;",
        "PromptAuditLog_CL",
        "| where TimeGenerated > ago(lookback)",
        "| summarize "
        "TotalCostUsd = sum(cost_usd_d), "
        "TotalPromptTokens = sum(prompt_tokens_d), "
        "TotalCompletionTokens = sum(completion_tokens_d) "
        "by user_id_s",
        f"| top {top_n} by TotalCostUsd desc",
    ])


def build_team_spend_query(lookback_days: int = 7) -> str:
    return "\n".join([
        f"let lookback = {lookback_days}d;",
        "PromptAuditLog_CL",
        "| where TimeGenerated > ago(lookback)",
        "| summarize TotalCostUsd = sum(cost_usd_d) by team_id_s",
        "| order by TotalCostUsd desc",
    ])


def run_query(logs_client: LogsQueryClient, workspace_id: str, query: str) -> list:
    response = logs_client.query_workspace(workspace_id, query, timespan=None)
    table = response.tables[0]
    return [dict(zip(table.columns, row)) for row in table.rows]


def main(req: func.HttpRequest) -> func.HttpResponse:
    scope = req.params.get("scope", "user")
    if scope not in ("user", "team"):
        return func.HttpResponse(
            json.dumps({"error": "scope must be 'user' or 'team'"}),
            status_code=400,
            mimetype="application/json",
        )

    lookback_days = int(req.params.get("lookback_days", "7"))
    workspace_id = os.environ["AZURE_LOG_ANALYTICS_WORKSPACE_ID"]

    query = (
        build_user_spend_query(lookback_days=lookback_days)
        if scope == "user"
        else build_team_spend_query(lookback_days=lookback_days)
    )
    rows = run_query(get_logs_client(), workspace_id, query)
    return func.HttpResponse(
        json.dumps({"scope": scope, "results": rows}),
        status_code=200,
        mimetype="application/json",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/test_user_stats_api.py -v`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/api/user_stats.py backend/tests/test_user_stats_api.py
git commit -m "feat: add user_stats REST API for per-user and per-team spend"
```

---

### Task 5: Wire `function_app.py`, document new env vars, run full suite

**Files:**
- Modify: `backend/function_app.py`
- Modify: `backend/local.settings.json.example`

**Interfaces:**
- Consumes: `anomaly_checker.function.main` (Task 2), `api.audit_log.main` (Task 3), `api.user_stats.main` (Task 4).
- Produces: the deployed Function App's final route/trigger set for Week 3 — `GET /api/audit_log`, `GET /api/user_stats`, and a timer trigger firing `anomaly_checker` hourly.

- [ ] **Step 1: Modify `backend/function_app.py`**

Add these imports alongside the existing ones:
```python
from anomaly_checker.function import main as anomaly_checker_main
from api.audit_log import main as audit_log_main
from api.user_stats import main as user_stats_main
```

Add these routes/trigger after the existing `log_ingest_consumer` function:
```python
@app.route(route="audit_log", methods=["GET"])
def audit_log(req: func.HttpRequest) -> func.HttpResponse:
    return audit_log_main(req)


@app.route(route="user_stats", methods=["GET"])
def user_stats(req: func.HttpRequest) -> func.HttpResponse:
    return user_stats_main(req)


@app.timer_trigger(schedule="0 0 * * * *", arg_name="timer", run_on_startup=False)
def anomaly_checker(timer: func.TimerRequest) -> None:
    anomaly_checker_main(timer)
```

- [ ] **Step 2: Modify `backend/local.settings.json.example`**

Add these keys to the `Values` object:
```json
    "AZURE_LOG_ANALYTICS_WORKSPACE_ID": "your-workspace-guid",
    "ANOMALY_BASELINE_CONTAINER": "governance-policies",
    "ANOMALY_BASELINE_BLOB": "usage-baselines.json",
    "AZURE_MONITOR_RESOURCE_ID": "/subscriptions/.../resourceGroups/rg-prompt-governance-dev/providers/Microsoft.Insights/components/prompt-governance-resource-appinsights",
    "AZURE_MONITOR_REGION": "eastus"
```

- [ ] **Step 3: Run the full non-integration test suite**

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/ -v --ignore=tests/integration`
Expected: all tests pass or skip cleanly (skips gated on `OPENAI_API_KEY`/Content Safety env vars, same as Week 1/2; no unexpected failures in any file this plan didn't touch).

- [ ] **Step 4: Commit**

```bash
git add backend/function_app.py backend/local.settings.json.example
git commit -m "feat: wire anomaly checker timer and audit_log/user_stats routes into function_app"
```

---

## Self-Review

**Spec coverage against Section 11 Week 3 (Day 1-5):**
- Day 1-2 (log-writer fully built, DCR verified, first 2 KQL queries, 50-prompt ingestion test) → log-writer/DCR already done in Week 1 (`log_writer/function.py`, `log_ingest_consumer/function.py`), not re-touched here; Task 1 ✓ covers `flag-summary.kql` and `user-spend.kql` (and the other 6, ahead of Day 5's schedule since they're all one cohesive file set). The 50-prompt live-ingestion test is a real-Azure-resource integration test outside this plan's local scope — same documented sandbox limitation as Week 1 Task 8's Event-Hub-to-Log-Analytics test; not re-created here since Week 1 already has that integration test in place.
- Day 3 (cost tracking + cost fields in AuditEvent/KQL) → `cost_usd`/`prompt_tokens`/`completion_tokens` already on `AuditEvent` and computed in `log_writer/function.py:build_audit_event` since Week 1; Task 1's `user-spend.kql`/`team-spend.kql` include `cost_usd_d`. No new task needed — flagged as already-satisfied rather than invented busywork.
- Day 4 (anomaly checker, hourly, 3x baseline, Log Analytics + Azure Monitor) → Task 2 ✓.
- Day 5 (remaining 6 KQL queries, `audit_log`/`user_stats` REST functions) → Task 1 (all 8, not just 6, written together) ✓, Task 3 ✓, Task 4 ✓.

**Deliberate exclusions**: this plan does not touch `app/`, `dashboard/`, `classification/`, `policy_engine/`, `log_writer/`, or `log_ingest_consumer/` — all already correct. It does not build `api/policy_config.py` — the spec's Week 3 day-by-day only asks for `audit_log.py` and `user_stats.py`; `policy_config.py` is implied by Week 4 Day 4's Policy Manager UI needing a save endpoint, so it's deferred to that week's plan. It does not provision any new Azure resources (Log Analytics workspace, Event Hub, and `PromptAuditLog_CL` table all already exist per Week 1) and does not attempt a live call to `LogsQueryClient`, Event Hub, or the Azure Monitor custom-metrics endpoint in the local test suite — all three are monkeypatched, consistent with the pattern established for `OPENAI_API_KEY`-gated tests in Weeks 1-2.

**Placeholder scan**: no TBD/TODO/"add error handling" placeholders. `audit-search.kql` (Task 1, Step 10) contains literal `REPLACE_WITH_*` tokens, but this is explicitly documented as a reference/documentation copy of the query shape that `api/audit_log.py`'s `build_audit_search_query` (Task 3) actually assembles at runtime with real, validated values — not a placeholder left for someone else to fill in later.

**Type consistency**: `build_anomaly_event()` (Task 2) returns `shared.models.AuditEvent` unchanged from Week 1 — same field names consumed by `log_writer.function.publish_to_event_hub()` (Week 1, unchanged). `get_active_users_24h()`'s `dict[str, int]` return (Task 2) matches how `main()` (Task 2, Step 6) iterates `totals.items()`. `run_query()` is defined independently but identically in `api/audit_log.py` (Task 3) and `api/user_stats.py` (Task 4) — this is a deliberate, small, intentional duplication (two-line function, two call sites) rather than a premature shared-helper abstraction; noting it here rather than silently duplicating without comment.
