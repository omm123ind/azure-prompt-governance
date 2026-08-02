# Architecture

## Data flow

```
Enterprise App
    │  POST /chat/completions
    ▼
Azure API Management (Consumption tier)
    │  inbound policy: send-request to classification function
    ▼
Classification Function (Python, Azure Functions)
    │  parallel: PII detector, jailbreak detector, Content Safety
    ▼
Policy Engine (Blob-backed rules, 60s TTL cache)
    │  action: block | flag | pass
    ├─ block ──────────────────────────────► 403 returned to caller
    └─ pass/flag ──► forwarded to OpenAI ──► response returned to caller
                            │
                            ▼
                    Log Writer Function
                            │  publish (hash-only AuditEvent)
                            ▼
                    Azure Event Hub
                            │
                            ▼
              Log Ingest Consumer Function
                            │  Logs Ingestion API
                            ▼
            Azure Log Analytics (PromptAuditLog_CL)
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
      Anomaly Checker   REST API      KQL Query
      (hourly timer)   (audit_log,    Library
              │        user_stats,   (8 queries)
              │        policy_config)      │
              ▼             │              ▼
      Event Grid ◄──────────┘      React Dashboard
              │                     (MSAL/AAD auth,
              ▼                      4 views)
      Teams Webhook
```

## Azure services

| Service | Role |
|---|---|
| API Management (Consumption) | Reverse proxy, inbound/outbound policy interception |
| Azure Functions (Python 3.11) | Classification, log-writer, log-ingest-consumer, anomaly-checker, REST API |
| Azure Event Hub (Basic) | Decouples the real-time prompt path from the audit-logging path |
| Azure AI Content Safety | Harm scoring (hate/violence/self-harm/sexual, 0-7) |
| Azure Log Analytics | Central audit store (`PromptAuditLog_CL`), 90-day retention |
| Azure Monitor | Custom metrics for anomaly detection |
| Azure Event Grid | Routes high-severity events to the dashboard and Teams |
| Azure Active Directory | OAuth2 login for the dashboard, `compliance-admin`/`audit-viewer` roles |
| Azure Key Vault | Secrets, accessed via Managed Identity (not yet wired — see Known Gaps) |
| Azure Blob Storage | Policy rules JSON + anomaly-checker usage baselines |
| Azure Static Web Apps | Dashboard hosting |

## Privacy design decisions

- **Raw prompt/response text is never persisted anywhere.** Every audit
  record stores only `prompt_hash`/`response_hash` (SHA-256). This is
  enforced at the model level (`backend/shared/models.py`'s `AuditEvent`
  has no `prompt`/`response` field at all, not just a policy not to fill
  one in) and verified by tests (`test_shared_models.py`,
  `test_log_writer.py`) that explicitly assert these fields aren't
  present.
- **User/team identifiers are expected to be pre-hashed** by the calling
  application before reaching this platform — `user_id`/`team_id` are
  passed through as opaque strings, never derived from PII.
- **The Audit Explorer dashboard view never renders prompt content** —
  only `prompt_hash_s` and classification metadata.
- **API access requires a real AAD access token** (not an ID token —
  `backend/api/auth.py` validates the `scp`/`roles` claim shape), with
  role-based access: `audit-viewer` can read audit data, only
  `compliance-admin` can read or change policy rules.

## Known gaps (not yet built)

- No Azure Key Vault / Managed Identity wiring — secrets currently come
  from `local.settings.json`/environment variables directly, matching
  the pattern used throughout Weeks 1-4, not yet migrated to Key Vault.
- No live Azure deployment exists — see the README's "Deploying to
  Azure" section for the manual steps required.
- Power BI Embedded (spec's preferred Cost Analytics visualization) was
  not built — the spec's own recharts fallback was used instead (see
  the Week 4 plan's self-review for the reasoning).
