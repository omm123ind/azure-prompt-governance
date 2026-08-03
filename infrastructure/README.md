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

## Why the outbound policy re-reads `classificationResult` from a variable

`IResponse.Body.As<T>()` consumes the underlying response stream. Any
code path that reads a response body more than once (once to check
`action == "block"`, again later to build the `log_writer` payload) must
pass `preserveContent: true` on every read, or the second read gets an
empty stream. The inbound policy stores the parsed classification result
in `context.Variables["classificationResult"]` specifically so the
outbound policy can reuse it without needing another read of the (by then
already-consumed) `classificationResponse` variable.
