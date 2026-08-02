# Classification Function Load Test

Measures the classification function's own p50/p95/p99 latency under 50
concurrent requests, per spec Section 11 Week 5 Day 1.

**Scope limitation:** no Function App has ever been deployed to Azure in
this project, so this cannot measure APIM's added latency — only the
classification function's own latency via a local `func start` host.
APIM Consumption-tier passthrough overhead is documented by Microsoft as
roughly 10-20ms and is not re-measured here.

## Running it

1. Start Azurite: `docker compose up -d azurite` (or the `npx azurite`
   equivalent — see the repo root `docker-compose.yml`).
2. Populate `backend/local.settings.json` with a real `OPENAI_API_KEY`
   and Content Safety credentials (gitignored, never committed) — this
   test makes real API calls, it is not mockable since it measures real
   classifier latency.
3. In a separate terminal: `cd backend && func start`
4. Run: `cd backend && .venv311/Scripts/python.exe tests/load/load_test_classification.py`

Exits 0 if p95 is within the 200ms threshold (spec Section 13.1), exits 1
with guidance toward the async fallback pattern if not.
