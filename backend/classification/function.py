import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import azure.functions as func

from classification.content_safety import analyze_content_safety
from classification.jailbreak_detector import detect_jailbreak
from classification.pii_detector import detect_pii


def classify(prompt_text: str) -> dict:
    start = time.time()

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(detect_pii, prompt_text): "pii",
            executor.submit(detect_jailbreak, prompt_text): "jailbreak",
            executor.submit(analyze_content_safety, prompt_text): "harm",
        }
        results = {}
        for future in as_completed(futures):
            key = futures[future]
            results[key] = future.result()

    latency_ms = int((time.time() - start) * 1000)

    pii = results["pii"]
    jailbreak = results["jailbreak"]
    harm = results["harm"]

    harm_scores = [
        harm["harm_hate_score"],
        harm["harm_violence_score"],
        harm["harm_selfharm_score"],
        harm["harm_sexual_score"],
    ]

    classification = {
        "pii_detected": pii["pii_detected"],
        "pii_confidence": pii["confidence"],
        "pii_categories": pii["categories_found"],
        "jailbreak_score": jailbreak["confidence"],
        "harm_hate_score": harm["harm_hate_score"],
        "harm_violence_score": harm["harm_violence_score"],
        "harm_selfharm_score": harm["harm_selfharm_score"],
        "harm_sexual_score": harm["harm_sexual_score"],
        "classification_latency_ms": latency_ms,
    }

    return {
        "classification": classification,
        "max_harm_score": max(harm_scores),
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

    logging.info("classification invoked, prompt length=%d", len(prompt_text))
    result = classify(prompt_text)
    return func.HttpResponse(
        json.dumps(result),
        status_code=200,
        mimetype="application/json",
    )
