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
