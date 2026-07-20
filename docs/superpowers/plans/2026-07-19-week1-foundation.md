# Week 1 Foundation & Provisioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Week 1 deliverable from `CLAUDE_CODE_CONTEXT.txt`: a prompt sent through Azure API Management reaches OpenAI and back, with a stub classification function in the loop, a stub log-writer receiving events, and local Azure Functions dev working end-to-end — without changing the classification/policy logic itself (that's Week 2).

**Architecture:** New `backend/` tree matches the spec's Azure Functions layout exactly (`classification/`, `log_writer/`, `anomaly_checker/`, `policy_engine/`, `api/`, `shared/`), scaffolded as local Python 3.11 Azure Functions (Python v2 programming model) run via Azure Functions Core Tools + Azurite for local Blob/Queue emulation. The existing `app/` FastAPI service is left untouched — it is not deleted or migrated in this plan, since that's a separate decision the user hasn't made yet. Azure-side: most Week 1 resources already exist in `rg-prompt-governance-dev` (see project memory `azure_resources.md`); this plan wires them up rather than recreating them — creates the missing `governance-policies` blob container, the missing `PromptAuditLog_CL` Log Analytics table + Data Collection Rule, and the missing APIM API/operation, then proves the full round trip.

**Tech Stack:** Python 3.11 (Azure Functions requirement — the machine currently only has 3.14, so a pinned 3.11 venv is step one), `azure-functions`, `azure-storage-blob`, `azure-eventhub`, `python-dotenv`, `pydantic`, Azure Functions Core Tools v4, Azurite, Azure CLI (`az`, already logged into subscription `66a892ff-3e36-4ba3-913b-986ff4c24c58`).

## Global Constraints

- OpenAI client: `from openai import OpenAI` only — never `AzureOpenAI`, never `api_type="azure"`.
- Model name stays `gpt-4o-mini` per spec (current `.env` has `gpt-5-mini` — flag but do not silently change without telling the user; this plan does not touch `.env`'s `MODEL` value).
- No raw prompt text may be persisted anywhere written in this plan — only `prompt_hash`/`response_hash` (SHA-256). The stub log-writer in this plan writes only hashes, never `req.prompt` itself.
- All new secrets/connection strings go in `backend/local.settings.json`, which must be gitignored — never hardcoded in `.py` files.
- Every resource-creation `az` command must be run with `--query` output shown and its exit code checked before the next step — do not assume success.
- Do not delete, rename, or modify any file under `app/` or `dashboard/` in this plan.

---

### Task 1: Pin Python 3.11 for the backend and verify Azure Functions Core Tools

**Files:**
- Create: `backend/.python-version` (content: `3.11`)

**Interfaces:**
- Produces: a `backend/.venv311` virtualenv at Python 3.11.x that all later tasks' `pip install`/`func start` commands use.

- [ ] **Step 1: Install Python 3.11 via winget** (the machine only has 3.14.6, and the Azure Functions Python worker does not support 3.14)

Run: `winget install --id Python.Python.3.11 -e --source winget`
Expected: install completes, exit code 0.

- [ ] **Step 2: Verify the 3.11 launcher is available**

Run: `py -3.11 --version`
Expected: `Python 3.11.x`

- [ ] **Step 3: Create the backend venv pinned to 3.11**

```bash
cd "C:\Users\Hunterr070\azure-prompt-governance"
py -3.11 -m venv backend/.venv311
```

- [ ] **Step 4: Write the version marker file**

`backend/.python-version`:
```
3.11
```

- [ ] **Step 5: Verify Azure Functions Core Tools sees the right runtime**

Run: `func --version`
Expected: `4.x.x` (already confirmed installed at 4.12.1 — this step just re-confirms after any environment change)

- [ ] **Step 6: Commit**

```bash
git add backend/.python-version
git commit -m "chore: pin backend to Python 3.11 for Azure Functions"
```

---

### Task 2: Scaffold `backend/shared` — models, OpenAI client, constants

**Files:**
- Create: `backend/shared/__init__.py`
- Create: `backend/shared/models.py`
- Create: `backend/shared/openai_client.py`
- Create: `backend/shared/constants.py`
- Create: `backend/requirements.txt`
- Test: `backend/tests/test_shared_models.py`

**Interfaces:**
- Produces: `AuditEvent` and `ClassificationResult` Pydantic models (exact field names below — Week 2/3 tasks depend on these), `get_openai_client() -> OpenAI` singleton, constants `DEFAULT_PII_BLOCK_THRESHOLD=0.8`, `DEFAULT_JAILBREAK_BLOCK_THRESHOLD=0.85`, `DEFAULT_HARM_BLOCK_THRESHOLD=6`, `CACHE_TTL_SECONDS=60`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_shared_models.py`:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.models import AuditEvent, ClassificationResult


def test_audit_event_requires_hash_not_raw_prompt():
    event = AuditEvent(
        event_id="11111111-1111-1111-1111-111111111111",
        session_id="22222222-2222-2222-2222-222222222222",
        user_id="hashed-user",
        team_id="hashed-team",
        prompt_hash="a" * 64,
        response_hash="b" * 64,
        pii_detected=False,
        pii_confidence=0.0,
        pii_categories=[],
        jailbreak_score=0.0,
        harm_hate_score=0,
        harm_violence_score=0,
        harm_selfharm_score=0,
        harm_sexual_score=0,
        action_taken="pass",
        block_reason=None,
        prompt_tokens=10,
        completion_tokens=5,
        cost_usd=0.0000021,
        model="gpt-4o-mini",
        latency_ms=87,
    )
    assert not hasattr(event, "prompt")
    assert not hasattr(event, "response")
    assert event.prompt_hash == "a" * 64


def test_classification_result_defaults():
    result = ClassificationResult(
        pii_detected=False,
        pii_confidence=0.0,
        pii_categories=[],
        jailbreak_score=0.0,
        harm_hate_score=0,
        harm_violence_score=0,
        harm_selfharm_score=0,
        harm_sexual_score=0,
        classification_latency_ms=0,
    )
    assert result.pii_categories == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/test_shared_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shared'`

- [ ] **Step 3: Write `backend/requirements.txt`** (UTF-8, one package per line — the repo-root `requirements.txt` is UTF-16 and broken; do not copy it)

```
openai>=1.30.0
azure-functions>=1.18.0
azure-eventhub>=5.11.0
azure-monitor-query>=1.3.0
azure-identity>=1.16.0
azure-storage-blob>=12.19.0
azure-ai-contentsafety>=1.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 4: Install dependencies**

```bash
cd backend
../backend/.venv311/Scripts/pip.exe install -r requirements.txt
```

- [ ] **Step 5: Write `backend/shared/__init__.py`** (empty file, makes `shared` a package)

- [ ] **Step 6: Write `backend/shared/constants.py`**

```python
DEFAULT_PII_BLOCK_THRESHOLD = 0.8
DEFAULT_JAILBREAK_BLOCK_THRESHOLD = 0.85
DEFAULT_HARM_BLOCK_THRESHOLD = 6
CACHE_TTL_SECONDS = 60
OPENAI_MODEL = "gpt-4o-mini"
```

- [ ] **Step 7: Write `backend/shared/models.py`**

```python
from typing import Optional
from pydantic import BaseModel


class AuditEvent(BaseModel):
    timestamp: Optional[str] = None
    event_id: str
    session_id: str
    user_id: str
    team_id: str
    prompt_hash: str
    response_hash: str
    pii_detected: bool
    pii_confidence: float
    pii_categories: list[str]
    jailbreak_score: float
    harm_hate_score: int
    harm_violence_score: int
    harm_selfharm_score: int
    harm_sexual_score: int
    action_taken: str
    block_reason: Optional[str] = None
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    model: str
    latency_ms: int


class ClassificationResult(BaseModel):
    pii_detected: bool
    pii_confidence: float
    pii_categories: list[str]
    jailbreak_score: float
    harm_hate_score: int
    harm_violence_score: int
    harm_selfharm_score: int
    harm_sexual_score: int
    classification_latency_ms: int
```

- [ ] **Step 8: Write `backend/shared/openai_client.py`**

```python
import os
from openai import OpenAI

_client = None


def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client
```

- [ ] **Step 9: Run test to verify it passes**

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/test_shared_models.py -v`
Expected: `2 passed`

- [ ] **Step 10: Commit**

```bash
git add backend/requirements.txt backend/shared backend/tests/test_shared_models.py
git commit -m "feat: scaffold backend/shared models, OpenAI client, constants"
```

---

### Task 3: Scaffold the classification function as a pass-through stub

**Files:**
- Create: `backend/classification/__init__.py`
- Create: `backend/classification/function.py`
- Create: `backend/host.json`
- Create: `backend/local.settings.json.example`
- Test: `backend/tests/test_classification_stub.py`

**Interfaces:**
- Consumes: nothing from other tasks yet (Week 2 will make this call `pii_detector`/`jailbreak_detector`/`content_safety`).
- Produces: `classify(prompt_text: str) -> dict` returning `{"action": "pass", "triggered_rule": None, "classification": {...}}` — this exact shape is what `log_writer` (Task 4) and the real classifiers (Week 2) will populate.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_classification_stub.py`:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from classification.function import classify


def test_stub_always_passes():
    result = classify("Summarise the key trends in renewable energy for 2025.")
    assert result["action"] == "pass"
    assert result["triggered_rule"] is None
    assert result["classification"]["pii_detected"] is False
    assert result["classification"]["jailbreak_score"] == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/test_classification_stub.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'classification'`

- [ ] **Step 3: Write `backend/classification/__init__.py`** (empty)

- [ ] **Step 4: Write `backend/classification/function.py`**

```python
import json
import logging
import time

import azure.functions as func


def classify(prompt_text: str) -> dict:
    """Week 1 stub: always passes. Week 2 replaces the body with real
    PII/jailbreak/harm classifiers run in parallel."""
    start = time.time()
    latency_ms = int((time.time() - start) * 1000)
    return {
        "action": "pass",
        "triggered_rule": None,
        "classification": {
            "pii_detected": False,
            "pii_confidence": 0.0,
            "pii_categories": [],
            "jailbreak_score": 0.0,
            "harm_hate_score": 0,
            "harm_violence_score": 0,
            "harm_selfharm_score": 0,
            "harm_sexual_score": 0,
            "classification_latency_ms": latency_ms,
        },
    }


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "invalid JSON body"}),
            status_code=400,
            mimetype="application/json",
        )

    prompt_text = body.get("prompt", "")
    if not prompt_text:
        return func.HttpResponse(
            json.dumps({"error": "missing 'prompt' field"}),
            status_code=400,
            mimetype="application/json",
        )

    logging.info("classification stub invoked, prompt length=%d", len(prompt_text))
    result = classify(prompt_text)
    return func.HttpResponse(
        json.dumps(result),
        status_code=200,
        mimetype="application/json",
    )
```

- [ ] **Step 5: Write `backend/host.json`**

```json
{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "excludedTypes": "Request"
      }
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  }
}
```

- [ ] **Step 6: Write `backend/local.settings.json.example`** (the real `local.settings.json` is gitignored — this example documents required keys)

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "OPENAI_API_KEY": "sk-...",
    "AZURE_STORAGE_CONNECTION_STRING": "UseDevelopmentStorage=true",
    "POLICY_BLOB_CONTAINER": "governance-policies",
    "POLICY_BLOB_NAME": "rules.json",
    "AZURE_EVENT_HUB_CONNECTION_STRING": "Endpoint=sb://...",
    "AZURE_EVENT_HUB_NAME": "eh-audit-events"
  }
}
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/test_classification_stub.py -v`
Expected: `1 passed`

- [ ] **Step 8: Commit**

```bash
git add backend/classification backend/host.json backend/local.settings.json.example backend/tests/test_classification_stub.py
git commit -m "feat: scaffold classification function as pass-through stub"
```

---

### Task 4: Scaffold the log-writer function (hash-only, no raw prompt storage)

**Files:**
- Create: `backend/log_writer/__init__.py`
- Create: `backend/log_writer/function.py`
- Test: `backend/tests/test_log_writer.py`

**Interfaces:**
- Consumes: `shared.models.AuditEvent` (Task 2).
- Produces: `build_audit_event(prompt: str, response: str, classification: dict, action: str, model: str, prompt_tokens: int, completion_tokens: int, latency_ms: int) -> AuditEvent` — Task 8 (Event Hub wiring) calls this.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_log_writer.py`:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from log_writer.function import build_audit_event, hash_text


def test_hash_text_is_sha256_hex():
    digest = hash_text("hello world")
    assert len(digest) == 64
    assert digest == "b94d27b9934d3e08a52e52d7da7dacefac9d51 68 45 1c 0 8 66138656805 6".replace(" ", "")


def test_build_audit_event_never_stores_raw_text():
    classification = {
        "pii_detected": False,
        "pii_confidence": 0.0,
        "pii_categories": [],
        "jailbreak_score": 0.0,
        "harm_hate_score": 0,
        "harm_violence_score": 0,
        "harm_selfharm_score": 0,
        "harm_sexual_score": 0,
        "classification_latency_ms": 5,
    }
    event = build_audit_event(
        prompt="my email is john@example.com",
        response="I can't help with that.",
        classification=classification,
        action="pass",
        model="gpt-4o-mini",
        prompt_tokens=12,
        completion_tokens=6,
        latency_ms=90,
    )
    dumped = event.model_dump()
    assert "prompt" not in dumped
    assert "response" not in dumped
    assert "john@example.com" not in str(dumped)
    assert len(event.prompt_hash) == 64
    assert len(event.response_hash) == 64
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/test_log_writer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'log_writer'`

- [ ] **Step 3: Write `backend/log_writer/__init__.py`** (empty)

- [ ] **Step 4: Write `backend/log_writer/function.py`**

```python
import hashlib
import json
import logging
import uuid

import azure.functions as func

from shared.models import AuditEvent


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_audit_event(
    prompt: str,
    response: str,
    classification: dict,
    action: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    user_id: str = "anonymous",
    team_id: str = "unassigned",
    block_reason: str | None = None,
) -> AuditEvent:
    cost_usd = (prompt_tokens * 0.00000015) + (completion_tokens * 0.0000006)
    return AuditEvent(
        event_id=str(uuid.uuid4()),
        session_id=str(uuid.uuid4()),
        user_id=user_id,
        team_id=team_id,
        prompt_hash=hash_text(prompt),
        response_hash=hash_text(response),
        pii_detected=classification["pii_detected"],
        pii_confidence=classification["pii_confidence"],
        pii_categories=classification["pii_categories"],
        jailbreak_score=classification["jailbreak_score"],
        harm_hate_score=classification["harm_hate_score"],
        harm_violence_score=classification["harm_violence_score"],
        harm_selfharm_score=classification["harm_selfharm_score"],
        harm_sexual_score=classification["harm_sexual_score"],
        action_taken=action,
        block_reason=block_reason,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        model=model,
        latency_ms=latency_ms,
    )


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "invalid JSON body"}),
            status_code=400,
            mimetype="application/json",
        )

    event = build_audit_event(
        prompt=body.get("prompt", ""),
        response=body.get("response", ""),
        classification=body["classification"],
        action=body.get("action", "pass"),
        model=body.get("model", "gpt-4o-mini"),
        prompt_tokens=body.get("prompt_tokens", 0),
        completion_tokens=body.get("completion_tokens", 0),
        latency_ms=body.get("latency_ms", 0),
    )
    logging.info("audit event built: %s", event.event_id)
    return func.HttpResponse(
        json.dumps({"received": True, "event_id": event.event_id}),
        status_code=200,
        mimetype="application/json",
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/test_log_writer.py -v`
Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/log_writer backend/tests/test_log_writer.py
git commit -m "feat: scaffold log-writer function, hash-only audit events"
```

---

### Task 5: docker-compose + Azurite for local dev

**Files:**
- Modify: `docker-compose.yml:1` (currently empty)
- Create: `.env.example`

**Interfaces:**
- Produces: an `azurite` service on ports 10000-10002 that Task 6's Blob test and local Functions runs both point at via `UseDevelopmentStorage=true`.

- [ ] **Step 1: Write `docker-compose.yml`**

```yaml
version: "3.8"

services:
  azurite:
    image: mcr.microsoft.com/azure-storage/azurite:latest
    ports:
      - "10000:10000"
      - "10001:10001"
      - "10002:10002"
    volumes:
      - azurite-data:/data
    command: "azurite --loose --blobHost 0.0.0.0 --queueHost 0.0.0.0 --tableHost 0.0.0.0 --location /data"

volumes:
  azurite-data:
```

- [ ] **Step 2: Write `.env.example`** (documents required root-level env vars without real values; the current `.env` has live secrets staged in git and must be unstaged separately — not part of this plan's scope, flagged to the user already)

```
OPENAI_API_KEY=sk-...
MODEL=gpt-4o-mini
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
AUDIT_CONTAINER=auditlogs
```

- [ ] **Step 3: Verify Azurite starts**

Run: `docker compose up -d azurite && docker compose ps`
Expected: `azurite` service state `running`/`Up`.

- [ ] **Step 4: Verify Azurite Blob endpoint responds**

Run: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:10000/devstoreaccount1`
Expected: a response code (400 is normal for an unauthenticated root request — anything other than connection-refused confirms Azurite is up)

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "feat: add Azurite docker-compose service for local Blob emulation"
```

---

### Task 6: Create the `governance-policies` Blob container and default `rules.json`

**Files:**
- Create: `backend/policy_engine/__init__.py`
- Create: `backend/policy_engine/rules.json`
- Create: `backend/policy_engine/engine.py`
- Test: `backend/tests/test_policy_engine.py`

**Interfaces:**
- Consumes: `AZURE_STORAGE_CONNECTION_STRING` env var (real one from `hubpromptgov0103361454`, per project memory `azure_resources.md`).
- Produces: `get_rules() -> list[dict]` with a 60s TTL cache (per spec Section 6/13.3, using a `threading.Lock` to avoid cache-stampede) — Week 2's classification function will call this.

- [ ] **Step 1: Write `backend/policy_engine/rules.json`** (the default rules, exact content from spec Section 5)

```json
{
  "version": "1.0",
  "updated_at": "2026-07-19T00:00:00Z",
  "rules": [
    {
      "id": "block_pii",
      "description": "Block prompts with high-confidence PII detection",
      "condition": "pii_confidence",
      "threshold": 0.8,
      "action": "block",
      "notify": true,
      "enabled": true
    },
    {
      "id": "flag_jailbreak",
      "description": "Flag jailbreak attempts above threshold",
      "condition": "jailbreak_score",
      "threshold": 0.6,
      "action": "flag",
      "notify": true,
      "enabled": true
    },
    {
      "id": "block_jailbreak_high",
      "description": "Block high-confidence jailbreak attempts",
      "condition": "jailbreak_score",
      "threshold": 0.85,
      "action": "block",
      "notify": true,
      "enabled": true
    },
    {
      "id": "flag_harm",
      "description": "Flag any harm category score above 4",
      "condition": "max_harm_score",
      "threshold": 4,
      "action": "flag",
      "notify": true,
      "enabled": true
    },
    {
      "id": "block_harm_high",
      "description": "Block severe harm content",
      "condition": "max_harm_score",
      "threshold": 6,
      "action": "block",
      "notify": true,
      "enabled": true
    }
  ]
}
```

- [ ] **Step 2: Create the real Blob container** (this is a real, billable-adjacent Azure action on account `hubpromptgov0103361454` — confirm with the user before running if not already approved for this session)

```bash
az storage container create \
  --account-name hubpromptgov0103361454 \
  --name governance-policies \
  --auth-mode login
```

Expected: JSON output with `"created": true`.

- [ ] **Step 3: Upload the default rules.json to the real container**

```bash
az storage blob upload \
  --account-name hubpromptgov0103361454 \
  --container-name governance-policies \
  --name rules.json \
  --file backend/policy_engine/rules.json \
  --auth-mode login \
  --overwrite
```

Expected: JSON output with the uploaded blob's ETag.

- [ ] **Step 4: Verify the upload by listing the container**

Run: `az storage blob list --account-name hubpromptgov0103361454 --container-name governance-policies --auth-mode login --query "[].name" -o tsv`
Expected: `rules.json`

- [ ] **Step 5: Write the failing test** (uses Azurite, not the real account, so it's fast and free — set `AZURE_STORAGE_CONNECTION_STRING=UseDevelopmentStorage=true` in the test environment)

`backend/tests/test_policy_engine.py`:
```python
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
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/test_policy_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'policy_engine'` (requires Azurite running from Task 5 — start it first with `docker compose up -d azurite`)

- [ ] **Step 7: Write `backend/policy_engine/__init__.py`** (empty)

- [ ] **Step 8: Write `backend/policy_engine/engine.py`**

```python
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
```

- [ ] **Step 9: Run test to verify it passes**

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/test_policy_engine.py -v`
Expected: `3 passed`

- [ ] **Step 10: Commit**

```bash
git add backend/policy_engine backend/tests/test_policy_engine.py
git commit -m "feat: policy engine with Blob-backed rules and TTL cache"
```

---

### Task 7: Create the `PromptAuditLog_CL` Log Analytics table and Data Collection Rule

**Files:**
- Create: `infrastructure/log-analytics-table-schema.json`

**Interfaces:**
- Produces: the `PromptAuditLog_CL` custom table in workspace `prompt-governance-resource-logs`, and a Data Collection Rule (`dcr-prompt-audit`) that ingests from Event Hub `eh-audit-events` into it — Task 8 publishes a test event through this pipeline.

- [ ] **Step 1: Write `infrastructure/log-analytics-table-schema.json`** (column names follow the spec's `_s`/`_d`/`_b`/`_t` suffix convention)

```json
{
  "properties": {
    "schema": {
      "name": "PromptAuditLog_CL",
      "columns": [
        { "name": "TimeGenerated", "type": "datetime" },
        { "name": "event_id_s", "type": "string" },
        { "name": "session_id_s", "type": "string" },
        { "name": "user_id_s", "type": "string" },
        { "name": "team_id_s", "type": "string" },
        { "name": "prompt_hash_s", "type": "string" },
        { "name": "response_hash_s", "type": "string" },
        { "name": "pii_detected_b", "type": "boolean" },
        { "name": "pii_confidence_d", "type": "real" },
        { "name": "pii_categories_s", "type": "string" },
        { "name": "jailbreak_score_d", "type": "real" },
        { "name": "harm_hate_score_d", "type": "real" },
        { "name": "harm_violence_score_d", "type": "real" },
        { "name": "harm_selfharm_score_d", "type": "real" },
        { "name": "harm_sexual_score_d", "type": "real" },
        { "name": "action_taken_s", "type": "string" },
        { "name": "block_reason_s", "type": "string" },
        { "name": "prompt_tokens_d", "type": "real" },
        { "name": "completion_tokens_d", "type": "real" },
        { "name": "cost_usd_d", "type": "real" },
        { "name": "model_s", "type": "string" },
        { "name": "latency_ms_d", "type": "real" }
      ]
    }
  }
}
```

- [ ] **Step 2: Create the custom table** (real, billable-adjacent action on workspace `prompt-governance-resource-logs` — confirm with the user before running if not already approved)

```bash
az monitor log-analytics workspace table create \
  -g rg-prompt-governance-dev \
  --workspace-name prompt-governance-resource-logs \
  --name PromptAuditLog_CL \
  --columns TimeGenerated=datetime event_id_s=string session_id_s=string user_id_s=string team_id_s=string prompt_hash_s=string response_hash_s=string pii_detected_b=boolean pii_confidence_d=real pii_categories_s=string jailbreak_score_d=real harm_hate_score_d=real harm_violence_score_d=real harm_selfharm_score_d=real harm_sexual_score_d=real action_taken_s=string block_reason_s=string prompt_tokens_d=real completion_tokens_d=real cost_usd_d=real model_s=string latency_ms_d=real
```

Expected: JSON output with `"name": "PromptAuditLog_CL"` and `"provisioningState": "Succeeded"`.

- [ ] **Step 3: Verify the table exists**

Run: `az monitor log-analytics workspace table show -g rg-prompt-governance-dev --workspace-name prompt-governance-resource-logs --name PromptAuditLog_CL --query "name" -o tsv`
Expected: `PromptAuditLog_CL`

- [ ] **Step 4: Get the workspace resource ID for the DCR target**

Run: `az monitor log-analytics workspace show -g rg-prompt-governance-dev -n prompt-governance-resource-logs --query id -o tsv`
Expected: a resource ID string starting `/subscriptions/...` — save it, needed for Task 8's DCR creation.

- [ ] **Step 5: Commit**

```bash
git add infrastructure/log-analytics-table-schema.json
git commit -m "feat: define PromptAuditLog_CL schema, provision custom table"
```

---

### Task 8: Wire Event Hub → Data Collection Rule → PromptAuditLog_CL, prove the pipeline

**Files:**
- Create: `backend/tests/integration/test_event_hub_to_log_analytics.py`

**Interfaces:**
- Consumes: `eh-audit-events` (Event Hub, namespace `ehns-prompt-gov-dev`), `PromptAuditLog_CL` table (Task 7).
- Produces: a proven event round trip — this is what Week 3's real log-writer relies on.

- [ ] **Step 1: Get the Event Hub connection string**

```bash
az eventhubs namespace authorization-rule keys list \
  -g rg-prompt-governance-dev \
  --namespace-name ehns-prompt-gov-dev \
  --name RootManageSharedAccessKey \
  --query primaryConnectionString -o tsv
```

Expected: a connection string starting `Endpoint=sb://ehns-prompt-gov-dev...` — put it in `backend/local.settings.json` as `AZURE_EVENT_HUB_CONNECTION_STRING` (gitignored file, do not commit it).

- [ ] **Step 2: Create the Data Collection Rule linking the Event Hub to the table** (real, billable-adjacent action — confirm with the user before running)

This requires an ARM/Bicep template since `az monitor data-collection rule create` needs a JSON body for a custom Event Hub → Log Analytics stream; write it to a temp file and apply:

```bash
cat > /tmp/dcr-prompt-audit.json << 'EOF'
{
  "location": "eastus",
  "properties": {
    "streamDeclarations": {
      "Custom-PromptAuditLog": {
        "columns": [
          { "name": "event_id_s", "type": "string" },
          { "name": "session_id_s", "type": "string" },
          { "name": "user_id_s", "type": "string" },
          { "name": "team_id_s", "type": "string" },
          { "name": "prompt_hash_s", "type": "string" },
          { "name": "response_hash_s", "type": "string" },
          { "name": "pii_detected_b", "type": "boolean" },
          { "name": "pii_confidence_d", "type": "real" },
          { "name": "pii_categories_s", "type": "string" },
          { "name": "jailbreak_score_d", "type": "real" },
          { "name": "harm_hate_score_d", "type": "real" },
          { "name": "harm_violence_score_d", "type": "real" },
          { "name": "harm_selfharm_score_d", "type": "real" },
          { "name": "harm_sexual_score_d", "type": "real" },
          { "name": "action_taken_s", "type": "string" },
          { "name": "block_reason_s", "type": "string" },
          { "name": "prompt_tokens_d", "type": "real" },
          { "name": "completion_tokens_d", "type": "real" },
          { "name": "cost_usd_d", "type": "real" },
          { "name": "model_s", "type": "string" },
          { "name": "latency_ms_d", "type": "real" }
        ]
      }
    },
    "destinations": {
      "logAnalytics": [
        {
          "workspaceResourceId": "<WORKSPACE_RESOURCE_ID_FROM_TASK_7_STEP_4>",
          "name": "prompt-gov-logs"
        }
      ]
    },
    "dataFlows": [
      {
        "streams": ["Custom-PromptAuditLog"],
        "destinations": ["prompt-gov-logs"],
        "outputStream": "Custom-PromptAuditLog_CL"
      }
    ]
  }
}
EOF

az monitor data-collection rule create \
  -g rg-prompt-governance-dev \
  --name dcr-prompt-audit \
  --rule-file /tmp/dcr-prompt-audit.json
```

Expected: JSON output with `"provisioningState": "Succeeded"`.

- [ ] **Step 3: Write the integration test that publishes and verifies ingestion**

`backend/tests/integration/test_event_hub_to_log_analytics.py`:
```python
import json
import os
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from azure.eventhub import EventHubProducerClient, EventData
from azure.monitor.query import LogsQueryClient
from azure.identity import AzureCliCredential

from log_writer.function import build_audit_event


def test_published_event_appears_in_log_analytics():
    event = build_audit_event(
        prompt="test canonical prompt for week 1 pipeline check",
        response="test response",
        classification={
            "pii_detected": False, "pii_confidence": 0.0, "pii_categories": [],
            "jailbreak_score": 0.0, "harm_hate_score": 0, "harm_violence_score": 0,
            "harm_selfharm_score": 0, "harm_sexual_score": 0,
            "classification_latency_ms": 1,
        },
        action="pass",
        model="gpt-4o-mini",
        prompt_tokens=10,
        completion_tokens=5,
        latency_ms=50,
    )

    conn_str = os.environ["AZURE_EVENT_HUB_CONNECTION_STRING"]
    producer = EventHubProducerClient.from_connection_string(
        conn_str, eventhub_name="eh-audit-events"
    )
    with producer:
        batch = producer.create_batch()
        batch.add(EventData(event.model_dump_json()))
        producer.send_batch(batch)

    time.sleep(120)  # first ingestion can take ~10 minutes per spec Section 11 Day 4-5; CI should poll instead

    credential = AzureCliCredential()
    logs_client = LogsQueryClient(credential)
    workspace_id = os.environ["AZURE_LOG_ANALYTICS_WORKSPACE_ID"]
    query = f"PromptAuditLog_CL | where event_id_s == '{event.event_id}' | take 1"
    response = logs_client.query_workspace(workspace_id, query, timespan=None)
    assert len(response.tables[0].rows) == 1
```

- [ ] **Step 4: Get the workspace GUID for the test env var**

Run: `az monitor log-analytics workspace show -g rg-prompt-governance-dev -n prompt-governance-resource-logs --query customerId -o tsv`
Expected: a GUID — set as `AZURE_LOG_ANALYTICS_WORKSPACE_ID` in `backend/local.settings.json`.

- [ ] **Step 5: Run the integration test** (first ingestion is slow — allow up to 10-15 minutes per spec Section 11)

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/integration/test_event_hub_to_log_analytics.py -v -s`
Expected: `1 passed` (if it fails on the first run because ingestion hasn't caught up yet, wait 10 minutes and rerun — this matches the spec's documented first-time DCR latency)

- [ ] **Step 6: Commit**

```bash
git add backend/tests/integration/test_event_hub_to_log_analytics.py
git commit -m "test: prove Event Hub to PromptAuditLog_CL ingestion pipeline"
```

---

### Task 8b: Build the missing Event Hub → Log Analytics consumer

**Discovered during Task 8 execution**: a Data Collection Rule does not automatically pull data from an Event Hub. The DCR created in Task 8 (`dcr-prompt-audit`, confirmed provisioned) only accepts data pushed to it via the Azure Monitor Logs Ingestion API. Nothing was consuming `eh-audit-events` and pushing to it — `PromptAuditLog_CL` was confirmed empty via direct KQL query. This task builds that missing consumer.

**Files:**
- Create: `backend/log_ingest_consumer/__init__.py`
- Create: `backend/log_ingest_consumer/function.py`
- Modify: `backend/requirements.txt` (add `azure-monitor-ingestion>=1.0.0`)
- Modify: `backend/tests/integration/test_event_hub_to_log_analytics.py` (remove the flawed direct-query-after-sleep approach; the new test should invoke the consumer function's ingestion logic directly rather than relying on an automatic Event Hub → DCR binding that doesn't exist)

**Interfaces:**
- Consumes: `shared.models.AuditEvent` (Task 2), the real DCR `dcr-prompt-audit`'s `immutableId` and stream name `Custom-PromptAuditLog` (Task 8), a Data Collection Endpoint (DCE) that must be created and linked to the DCR before ingestion will work.
- Produces: `push_to_log_analytics(event: AuditEvent) -> None` using `azure.monitor.ingestion.LogsIngestionClient` — this is what an Event-Hub-triggered function body calls per received message.

- [ ] **Step 1: Create the Data Collection Endpoint** (real Azure action, region must match the DCR's `eastus`)

```bash
az monitor data-collection endpoint create \
  -g rg-prompt-governance-dev \
  --name dce-prompt-audit \
  --location eastus \
  --public-network-access Enabled
```

Expected: JSON with `"provisioningState": "Succeeded"` and a `logsIngestion.endpoint` URL in the output — save this URL.

- [ ] **Step 2: Link the DCE to the existing DCR**

```bash
DCE_ID=$(az monitor data-collection endpoint show -g rg-prompt-governance-dev -n dce-prompt-audit --query id -o tsv)
az monitor data-collection rule update \
  -g rg-prompt-governance-dev \
  --name dcr-prompt-audit \
  --data-collection-endpoint-id "$DCE_ID"
```

Expected: JSON showing `"dataCollectionEndpointId"` set to the DCE's resource ID.

- [ ] **Step 3: Add the ingestion SDK to requirements**

Add to `backend/requirements.txt`:
```
azure-monitor-ingestion>=1.0.0
```

Install: `backend/.venv311/Scripts/pip.exe install azure-monitor-ingestion>=1.0.0`

- [ ] **Step 4: Write `backend/log_ingest_consumer/__init__.py`** (empty)

- [ ] **Step 5: Write `backend/log_ingest_consumer/function.py`**

```python
import json
import logging
import os

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.monitor.ingestion import LogsIngestionClient


def push_to_log_analytics(event_dict: dict) -> None:
    endpoint = os.environ["AZURE_DCE_LOGS_INGESTION_ENDPOINT"]
    rule_id = os.environ["AZURE_DCR_IMMUTABLE_ID"]
    stream_name = "Custom-PromptAuditLog"

    credential = DefaultAzureCredential()
    client = LogsIngestionClient(endpoint=endpoint, credential=credential)

    row = {
        "event_id_s": event_dict["event_id"],
        "session_id_s": event_dict["session_id"],
        "user_id_s": event_dict["user_id"],
        "team_id_s": event_dict["team_id"],
        "prompt_hash_s": event_dict["prompt_hash"],
        "response_hash_s": event_dict["response_hash"],
        "pii_detected_b": event_dict["pii_detected"],
        "pii_confidence_d": event_dict["pii_confidence"],
        "pii_categories_s": json.dumps(event_dict["pii_categories"]),
        "jailbreak_score_d": event_dict["jailbreak_score"],
        "harm_hate_score_d": event_dict["harm_hate_score"],
        "harm_violence_score_d": event_dict["harm_violence_score"],
        "harm_selfharm_score_d": event_dict["harm_selfharm_score"],
        "harm_sexual_score_d": event_dict["harm_sexual_score"],
        "action_taken_s": event_dict["action_taken"],
        "block_reason_s": event_dict.get("block_reason") or "",
        "prompt_tokens_d": event_dict["prompt_tokens"],
        "completion_tokens_d": event_dict["completion_tokens"],
        "cost_usd_d": event_dict["cost_usd"],
        "model_s": event_dict["model"],
        "latency_ms_d": event_dict["latency_ms"],
    }
    client.upload(rule_id=rule_id, stream_name=stream_name, logs=[row])


def main(event: func.EventHubEvent):
    body = event.get_body().decode("utf-8")
    event_dict = json.loads(body)
    logging.info("consuming audit event %s from Event Hub", event_dict.get("event_id"))
    push_to_log_analytics(event_dict)
```

- [ ] **Step 6: Rewrite the integration test to call the consumer directly** (proves the ingestion logic works without depending on a local Event-Hub-triggered Functions host, which Azure Functions Core Tools CAN run locally against a real Event Hub, but that's a heavier local-runtime test better suited to Week 5's CI — this test proves the Logs Ingestion API call itself is correct)

Replace `backend/tests/integration/test_event_hub_to_log_analytics.py` with:
```python
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from azure.monitor.query import LogsQueryClient
from azure.identity import AzureCliCredential

from log_writer.function import build_audit_event
from log_ingest_consumer.function import push_to_log_analytics


def test_pushed_event_appears_in_log_analytics():
    event = build_audit_event(
        prompt="test canonical prompt for week 1 pipeline check",
        response="test response",
        classification={
            "pii_detected": False, "pii_confidence": 0.0, "pii_categories": [],
            "jailbreak_score": 0.0, "harm_hate_score": 0, "harm_violence_score": 0,
            "harm_selfharm_score": 0, "harm_sexual_score": 0,
            "classification_latency_ms": 1,
        },
        action="pass",
        model="gpt-4o-mini",
        prompt_tokens=10,
        completion_tokens=5,
        latency_ms=50,
    )

    push_to_log_analytics(event.model_dump())

    time.sleep(180)  # Log Analytics ingestion lag, even via direct API push

    credential = AzureCliCredential()
    logs_client = LogsQueryClient(credential)
    workspace_id = os.environ["AZURE_LOG_ANALYTICS_WORKSPACE_ID"]
    query = f"PromptAuditLog_CL | where event_id_s == '{event.event_id}' | take 1"
    response = logs_client.query_workspace(workspace_id, query, timespan=None)
    assert len(response.tables[0].rows) == 1
```

- [ ] **Step 7: Get the DCE logs ingestion endpoint and DCR immutableId, add to `backend/local.settings.json`**

```bash
az monitor data-collection endpoint show -g rg-prompt-governance-dev -n dce-prompt-audit --query logsIngestion.endpoint -o tsv
az monitor data-collection rule show -g rg-prompt-governance-dev --name dcr-prompt-audit --query immutableId -o tsv
```

Add both as `AZURE_DCE_LOGS_INGESTION_ENDPOINT` and `AZURE_DCR_IMMUTABLE_ID` to `backend/local.settings.json` (gitignored).

- [ ] **Step 8: Grant the logged-in identity the Monitoring Metrics Publisher role on the DCR** (required for `LogsIngestionClient` data-plane push — this is the DCR-equivalent of the Blob RBAC gap hit in Task 6; if you hit a permissions error here, do NOT self-assign — report it and let the user grant it, same pattern as Task 6)

```bash
az role assignment create \
  --assignee omm123ind@hotmail.com \
  --role "Monitoring Metrics Publisher" \
  --scope /subscriptions/66a892ff-3e36-4ba3-913b-986ff4c24c58/resourceGroups/rg-prompt-governance-dev/providers/Microsoft.Insights/dataCollectionRules/dcr-prompt-audit
```

- [ ] **Step 9: Run the test, time-boxed** (max ~2 attempts, ~3-5 min wait each, per Task 8's original time-boxing rule — do not loop indefinitely)

Run: `cd backend && ../backend/.venv311/Scripts/python.exe -m pytest tests/integration/test_event_hub_to_log_analytics.py -v -s`
Expected: `1 passed`, or a clear report of 0 rows after two attempts with the exact query used.

- [ ] **Step 10: Commit**

```bash
git add backend/log_ingest_consumer backend/requirements.txt backend/tests/integration/test_event_hub_to_log_analytics.py
git commit -m "feat: add Event Hub consumer pushing to Log Analytics via Logs Ingestion API"
```

---

### Task 9: Configure the APIM API and prove the full round trip

**Files:**
- Create: `infrastructure/apim-policy-inbound.xml`
- Create: `infrastructure/apim-policy-outbound.xml`

**Interfaces:**
- Produces: `POST https://apim-prompt-gov-dev.azure-api.net/openai/chat/completions` — the Week 1 end-of-week deliverable endpoint.

- [ ] **Step 1: Create the API on the existing APIM instance** (real, billable-adjacent action — confirm with the user before running)

```bash
az apim api create \
  -g rg-prompt-governance-dev \
  --service-name apim-prompt-gov-dev \
  --api-id prompt-governance-api \
  --path openai \
  --display-name "Prompt Governance API" \
  --service-url https://api.openai.com/v1 \
  --protocols https
```

Expected: JSON output with `"name": "prompt-governance-api"`.

- [ ] **Step 2: Add the POST /chat/completions operation**

```bash
az apim api operation create \
  -g rg-prompt-governance-dev \
  --service-name apim-prompt-gov-dev \
  --api-id prompt-governance-api \
  --url-template "/chat/completions" \
  --method POST \
  --display-name "Chat Completions" \
  --operation-id chat-completions
```

Expected: JSON output with `"name": "chat-completions"`.

- [ ] **Step 3: Write `infrastructure/apim-policy-inbound.xml`** (Week 1 version calls the stub classification function, which always passes — Week 2 adds real blocking behavior once the classifiers are real)

```xml
<policies>
  <inbound>
    <base />
    <send-request mode="new" response-variable-name="classificationResponse" timeout="5" ignore-error="false">
      <set-url>https://FUNCTION_APP_HOSTNAME/api/classification</set-url>
      <set-method>POST</set-method>
      <set-header name="Content-Type" exists-action="override">
        <value>application/json</value>
      </set-header>
      <set-body>@(context.Request.Body.As<string>(preserveContent: true))</set-body>
    </send-request>
    <choose>
      <when condition="@(((IResponse)context.Variables["classificationResponse"]).Body.As<JObject>()["action"].ToString() == "block")">
        <return-response>
          <set-status code="403" reason="Forbidden" />
          <set-body>@(((IResponse)context.Variables["classificationResponse"]).Body.As<string>())</set-body>
        </return-response>
      </when>
    </choose>
    <set-header name="Authorization" exists-action="override">
      <value>@("Bearer " + context.Variables.GetValueOrDefault<string>("openai-api-key"))</value>
    </set-header>
  </inbound>
  <backend>
    <base />
  </backend>
  <outbound>
    <base />
  </outbound>
  <on-error>
    <base />
  </on-error>
</policies>
```

- [ ] **Step 4: Write `infrastructure/apim-policy-outbound.xml`**

```xml
<policies>
  <inbound>
    <base />
  </inbound>
  <backend>
    <base />
  </backend>
  <outbound>
    <base />
    <send-one-way-request mode="new">
      <set-url>https://FUNCTION_APP_HOSTNAME/api/log_writer</set-url>
      <set-method>POST</set-method>
      <set-header name="Content-Type" exists-action="override">
        <value>application/json</value>
      </set-header>
      <set-body>@(context.Response.Body.As<string>(preserveContent: true))</set-body>
    </send-one-way-request>
  </outbound>
  <on-error>
    <base />
  </on-error>
</policies>
```

Note: `FUNCTION_APP_HOSTNAME` is a placeholder — Week 1's local Functions run via `func start` are not internet-reachable from APIM's Consumption tier, so this policy cannot go live against `localhost`. Deploying an actual Function App to Azure (so APIM can reach it) is a Week 5 CI/CD task (`deploy-functions.yml`) per the spec, not Week 1. For now, verify APIM's raw pass-through to OpenAI without the policies applied (Step 5), and apply the inbound/outbound XML only once a Function App is deployed.

- [ ] **Step 5: Verify APIM reaches OpenAI without policies** (proves Week 1's minimum deliverable: "call APIM endpoint with subscription key, confirm response from OpenAI")

```bash
az apim api operation policy create \
  -g rg-prompt-governance-dev \
  --service-name apim-prompt-gov-dev \
  --api-id prompt-governance-api \
  --operation-id chat-completions \
  --value '<policies><inbound><base /><set-header name="Authorization" exists-action="override"><value>@("Bearer " + "'"$OPENAI_API_KEY"'")</value></set-header></inbound><backend><base /></backend><outbound><base /></outbound><on-error><base /></on-error></policies>' \
  --format rawxml
```

- [ ] **Step 6: Get the APIM subscription key**

Run: `az apim subscription list -g rg-prompt-governance-dev --service-name apim-prompt-gov-dev --query "[0].{name:name}" -o tsv` then `az rest --method post --uri "https://management.azure.com$(az apim subscription list -g rg-prompt-governance-dev --service-name apim-prompt-gov-dev --query "[0].id" -o tsv)/listSecrets?api-version=2022-08-01" --query primaryKey -o tsv`
Expected: a subscription key string.

- [ ] **Step 7: Call APIM end to end**

```bash
curl -s -X POST "https://apim-prompt-gov-dev.azure-api.net/openai/chat/completions" \
  -H "Ocp-Apim-Subscription-Key: <KEY_FROM_STEP_6>" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Say hello in exactly 3 words."}]}'
```

Expected: HTTP 200 with a JSON body containing OpenAI's chat completion response.

- [ ] **Step 8: Commit**

```bash
git add infrastructure/apim-policy-inbound.xml infrastructure/apim-policy-outbound.xml
git commit -m "feat: configure APIM prompt-governance-api, verify OpenAI round trip"
```

---

## Self-Review

**Spec coverage against Section 11 Week 1 (Day 1-5):**
- Day 1-2 (APIM provisioning + test) → Task 9 ✓ (APIM already existed, this task adds the API/operation and proves the round trip)
- Day 2-3 (Functions scaffold + local.settings.json + local test) → Tasks 1, 3, 4 ✓
- Day 3-4 (GitHub repo/.gitignore — already exists from prior session; docker-compose+Azurite; Blob container + rules.json read test) → Tasks 5, 6 ✓
- Day 4-5 (Log Analytics workspace + custom table + DCR; Event Hub; publish+ingest test) → Tasks 7, 8 ✓ (Log Analytics workspace and Event Hub namespace already existed, this task adds the missing table/DCR)

**Deliberate exclusions**: Week 1's plan does not touch `app/` (existing FastAPI service), does not rotate or unstage the leaked `.env` secrets (flagged separately to the user, is the user's action to take), does not fix Key Vault access permissions (not required until Functions actually use Managed Identity, which is a later-week concern), and does not deploy a Function App to Azure (APIM cannot reach `localhost`, so the inbound/outbound policies are written but only fully activated once Week 5's `deploy-functions.yml` exists).

**Placeholder scan**: `FUNCTION_APP_HOSTNAME` in Task 9's XML policies is an intentional, explicitly-explained placeholder (not a banned "TBD") because the target doesn't exist yet in Week 1 — this is called out in the step text, not left implicit.

**Type consistency**: `AuditEvent` (Task 2) is consumed unchanged by `build_audit_event` (Task 4) and by the integration test (Task 8) — field names match throughout. `ClassificationResult`-shaped dict from `classify()` (Task 3) matches the `classification` dict shape consumed by `build_audit_event` (Task 4) and `evaluate()` (Task 6, via `pii_confidence`/`jailbreak_score`/`max_harm_score` keys — note `evaluate()` expects a flattened dict with `max_harm_score`, not the four separate harm scores; Week 2's real classification function must compute `max_harm_score = max(harm_hate_score, harm_violence_score, harm_selfharm_score, harm_sexual_score)` before calling `evaluate()` — flagging this for whoever picks up Week 2).
