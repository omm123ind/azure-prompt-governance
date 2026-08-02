"""
Load test for the classification function's own latency (the variable
component of the Week 2 spec's "APIM + classification" latency budget).

This does NOT measure APIM overhead — no Function App has ever been deployed
to Azure in this project, so there is no live APIM-to-Function round trip to
measure. APIM's own added latency for a Consumption-tier passthrough policy
is a well-documented ~10-20ms and is not re-measured here.

Prerequisites:
    1. Azurite running (docker compose up -d azurite, or
       npx azurite --skipApiVersionCheck --blobHost 127.0.0.1 ...)
    2. backend/local.settings.json populated with a real OPENAI_API_KEY and
       Content Safety credentials (this test makes real OpenAI/Content Safety
       API calls — it is not free and not mockable, since it measures real
       classifier latency)
    3. In a separate terminal, from backend/: func start
    4. Then run: python tests/load/load_test_classification.py
"""
import json
import math
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

DEFAULT_URL = "http://localhost:7071/api/classification"
DEFAULT_PROMPT = "Summarise the key trends in renewable energy for 2025."
DEFAULT_CONCURRENCY = 50
P95_THRESHOLD_MS = 200


def _send_one(url: str, prompt: str) -> tuple[bool, float]:
    body = json.dumps({"prompt": prompt}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            response.read()
            elapsed_ms = (time.monotonic() - start) * 1000
            return response.status == 200, elapsed_ms
    except (urllib.error.URLError, TimeoutError):
        elapsed_ms = (time.monotonic() - start) * 1000
        return False, elapsed_ms


def run_load_test(url: str, prompt: str, concurrency: int = DEFAULT_CONCURRENCY) -> dict:
    latencies = []
    success_count = 0
    error_count = 0

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(_send_one, url, prompt) for _ in range(concurrency)]
        for future in as_completed(futures):
            ok, elapsed_ms = future.result()
            latencies.append(elapsed_ms)
            if ok:
                success_count += 1
            else:
                error_count += 1

    latencies.sort()
    return {
        "p50_ms": statistics.median(latencies),
        "p95_ms": latencies[min(math.ceil(0.95 * len(latencies)) - 1, len(latencies) - 1)],
        "p99_ms": latencies[min(math.ceil(0.99 * len(latencies)) - 1, len(latencies) - 1)],
        "success_count": success_count,
        "error_count": error_count,
    }


def main():
    print(f"Load testing {DEFAULT_URL} with {DEFAULT_CONCURRENCY} concurrent requests...")
    print("(measures classification function latency only — see module docstring)")
    results = run_load_test(DEFAULT_URL, DEFAULT_PROMPT, DEFAULT_CONCURRENCY)

    print(f"\nResults ({results['success_count']} succeeded, {results['error_count']} failed):")
    print(f"  p50: {results['p50_ms']:.1f}ms")
    print(f"  p95: {results['p95_ms']:.1f}ms")
    print(f"  p99: {results['p99_ms']:.1f}ms")

    if results["p95_ms"] > P95_THRESHOLD_MS:
        print(
            f"\np95 latency ({results['p95_ms']:.1f}ms) exceeds the "
            f"{P95_THRESHOLD_MS}ms threshold — per spec Section 13.1, this "
            f"means an async classification fallback should be implemented "
            f"(APIM forwards to OpenAI immediately, classification fires "
            f"from an Event Hub trigger in parallel, audit record written "
            f"with a slight delay)."
        )
        sys.exit(1)

    print(f"\np95 latency is within the {P95_THRESHOLD_MS}ms threshold.")
    sys.exit(0)


if __name__ == "__main__":
    main()
