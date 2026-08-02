# Azure AI Prompt Governance Platform

A real-time governance layer between enterprise applications and OpenAI's
API: every prompt is intercepted, classified for PII/jailbreak/harm,
logged to a privacy-preserving audit trail, checked against a live-editable
policy engine, and surfaced on a compliance dashboard — with cost tracking
and anomaly detection built in.

See [`docs/architecture.md`](docs/architecture.md) for the full system
diagram, data flow, and privacy design decisions.

## What's built

- **Interception & classification** (`backend/classification/`) — PII,
  jailbreak/prompt-injection, and harm detection running in parallel via
  OpenAI few-shot classifiers + Azure AI Content Safety.
- **Policy engine** (`backend/policy_engine/`) — Blob-backed, live-editable
  rules with a 60-second cache, no redeploy needed for a threshold change.
- **Audit trail & cost tracking** (`backend/log_writer/`,
  `backend/log_ingest_consumer/`, `infrastructure/kql-queries/`) — every
  classified prompt written to Azure Log Analytics as a hash-only record
  (raw prompt/response text is never stored), with an 8-query KQL library
  powering the dashboard.
- **Anomaly detection** (`backend/anomaly_checker/`) — hourly check of
  each user's 24h token usage against a rolling 7-day baseline, alerting
  at 3x.
- **REST API** (`backend/api/`) — `audit_log`, `user_stats`,
  `policy_config`, all gated behind AAD bearer-token RBAC
  (`backend/api/auth.py`).
- **Dashboard** (`dashboard/`) — React + TypeScript + MUI, MSAL/Azure AD
  login, 4 views (Live Feed, Audit Explorer, Policy Manager, Cost
  Analytics).
- **Alerting** (`backend/alerting/`) — Teams Adaptive Card builder +
  Event Grid publisher for high-severity events (jailbreak ≥ 0.85, PII
  blocked, harm ≥ 5).

## Environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | `backend/classification/` | Direct OpenAI API access (never Azure OpenAI) |
| `AZURE_CONTENT_SAFETY_ENDPOINT` / `_KEY` | `backend/classification/content_safety.py` | Harm scoring |
| `AZURE_STORAGE_CONNECTION_STRING` | `backend/policy_engine/`, `backend/anomaly_checker/` | Policy rules blob, usage baseline blob |
| `AZURE_EVENT_HUB_CONNECTION_STRING` | `backend/log_writer/`, `backend/anomaly_checker/` | Audit/anomaly event publish |
| `AZURE_DCE_LOGS_INGESTION_ENDPOINT` / `AZURE_DCR_IMMUTABLE_ID` | `backend/log_ingest_consumer/` | Event Hub → Log Analytics ingestion |
| `AZURE_LOG_ANALYTICS_WORKSPACE_ID` | `backend/api/audit_log.py`, `user_stats.py`, `backend/anomaly_checker/` | KQL queries |
| `AZURE_AD_TENANT_ID` / `AZURE_AD_CLIENT_ID` | `backend/api/auth.py` | RBAC bearer-token validation — **must match** `VITE_AAD_TENANT_ID`/`VITE_AAD_CLIENT_ID` below (same AAD app registration), and the app registration's manifest must have `"accessTokenAcceptedVersion": 2` |
| `AZURE_EVENT_GRID_TOPIC_ENDPOINT` / `_KEY` | `backend/alerting/` | High-severity alert publish |
| `VITE_AAD_CLIENT_ID` / `VITE_AAD_TENANT_ID` | `dashboard/src/auth/msalConfig.ts` | MSAL login — same app registration as `AZURE_AD_CLIENT_ID`/`_TENANT_ID` above |
| `VITE_API_BASE_URL` | `dashboard/src/services/apiClient.ts` | Backend API base URL |

See `backend/local.settings.json.example` and `dashboard/.env.example`
for the full list with placeholder values.

## Running locally

Backend:
```bash
cd backend
python -m venv .venv311  # Python 3.11 required for Azure Functions
.venv311/Scripts/pip install -r requirements.txt
docker compose up -d azurite  # from repo root, for local Blob emulation
func start
```

Backend tests:
```bash
cd backend
../backend/.venv311/Scripts/python.exe -m pytest tests/ --ignore=tests/integration --ignore=tests/load -q
```

Dashboard:
```bash
cd dashboard
npm install
npm run dev
```

Dashboard tests:
```bash
cd dashboard
npm test
npx tsc -b --noEmit
```

## Deploying to Azure

This repo has never been deployed to a live Azure Function App or Static
Web App — Weeks 1-4 were built and tested entirely locally. To deploy:

1. Create a Function App (Python 3.11, Consumption plan) and a Static
   Web App in your Azure subscription.
2. Add `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` and
   `AZURE_STATIC_WEB_APPS_API_TOKEN` as GitHub repository secrets — this
   is what `.github/workflows/deploy-functions.yml` and
   `deploy-frontend.yml` need to actually deploy on push to `main`.
3. Register an AAD app for the dashboard (see `docs/architecture.md`'s
   privacy/identity section) and set `accessTokenAcceptedVersion: 2` in
   its manifest.
4. Provision an Event Grid topic and a Teams incoming webhook connector
   for high-severity alerts (see `backend/alerting/`'s module docstrings).

None of these four steps are automated by this repo — they're one-time
Azure/AAD/Teams portal actions outside what CI or application code can do.
