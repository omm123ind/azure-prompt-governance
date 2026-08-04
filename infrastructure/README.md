# Infrastructure

## APIM policy deployment note

`apim-policy-inbound.xml` and `apim-policy-outbound.xml` are kept as two
files for readability, but Azure API Management applies **one** policy
document per operation. To deploy, merge the `<inbound>` section from
`apim-policy-inbound.xml` and the `<outbound>` section from
`apim-policy-outbound.xml` into a single `<policies>` document (keep the
other's `<inbound>`/`<outbound>` as empty `<base />` passthroughs), then
apply it to the `chat-completions` operation on `prompt-governance-api`.

Both files reference named values that must exist in APIM before applying:

| Named value | Value |
|---|---|
| `openai-api-key` | Your OpenAI API key (secret) |
| `classification-function-key` | The deployed Function App's `classification` function key (secret) |
| `logwriter-function-key` | The deployed Function App's `log_writer` function key (secret) |

Create them with `az apim nv create ... --secret true`, or via the Azure
Portal (APIM → Named values).

The inbound policy also assumes the classification function is reachable
at a fixed hostname — update `https://prompt-governance-functions.azurewebsites.net`
in both files if the Function App name/hostname changes.

## Why the inbound policy extracts `prompt` from `messages`

The client sends an OpenAI-format chat completion body
(`{"model": ..., "messages": [...]}`), but the deployed `classification`
function expects `{"prompt": "..."}`. The inbound policy extracts the
last `role: "user"` message's `content` and forwards only that as
`prompt` — this transformation is required, not optional; forwarding the
raw request body to `classification` returns a 400.

## CI backend deploy requires `scm-do-build-during-deployment: true` as an action input

`.github/workflows/deploy-functions.yml` deploys with `Azure/functions-action@v1`.
On Linux Consumption, that action's zip-deploy call does **not** request an
Oryx remote build unless `scm-do-build-during-deployment: true` is passed as
an **input to the action step itself** — setting
`SCM_DO_BUILD_DURING_DEPLOYMENT`/`ENABLE_ORYX_BUILD` as Function App settings
alone has no effect on the action's own deploy request.

Symptom when this is missing: the deploy step reports "success", the Function
App stays in state `Running`, and `az functionapp function list` still shows
all functions registered (that's ARM/sync metadata, not the live host).
But the live host's function index is actually empty
(`GET /admin/functions?code=<masterKey>` returns `[]`), so every route
404s — because the deployed package is just the raw checked-in source with
no installed dependencies (confirmed via the Kudu deployment log: a plain
`rsync` of ~90 files, vs. the ~6000+ files and tens of MB you'd see from a
package with `azure-functions`, `openai`, etc. actually installed). The
worker fails to import the app and silently indexes zero functions — no
error surfaces at the host-status level.

Fix: keep `scm-do-build-during-deployment: true` on the `Azure/functions-action@v1`
step in `deploy-functions.yml`, and don't pre-vendor dependencies into
`backend/.python_packages/lib/site-packages` in the workflow — the Python
worker prioritizes that folder over Oryx's build output, so having both
present risks two conflicting dependency trees.

## Blocked prompts need their own `log_writer` call in `inbound`

The `outbound` section's `log_writer` call only runs for requests that reach
the backend (OpenAI) and come back — but the `block` branch in `inbound`
issues `<return-response>`, which short-circuits the pipeline and skips
`outbound` entirely. Without a separate `log_writer` call inside the `block`
`<when>` (before the `<return-response>`), blocked prompts — the PII and
jailbreak cases that are the entire point of this platform — never got an
audit record or a Teams alert, while clean prompts logged fine. Found via a
live demo rehearsal: Scenario 1 (clean prompt) appeared in the audit trail,
but Scenarios 2/3 (PII block, jailbreak block) never did.

The inbound `log_writer` call omits `response`/`model`/token counts/latency
(defaults to `""`/`"gpt-4o-mini"`/`0`s in `log_writer`'s payload handling)
since the backend was never called — the prompt was blocked before reaching
OpenAI, which `log_writer`'s existing `.get(...)` defaults already handle.

## Why the outbound policy re-reads `classificationResult` from a variable

`IResponse.Body.As<T>()` consumes the underlying response stream. Any
code path that reads a response body more than once (once to check
`action == "block"`, again later to build the `log_writer` payload) must
pass `preserveContent: true` on every read, or the second read gets an
empty stream. The inbound policy stores the parsed classification result
in `context.Variables["classificationResult"]` specifically so the
outbound policy can reuse it without needing another read of the (by then
already-consumed) `classificationResponse` variable.
