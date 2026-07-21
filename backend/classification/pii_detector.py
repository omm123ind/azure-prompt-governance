import json
import logging

from shared.constants import OPENAI_MODEL
from shared.openai_client import get_openai_client

SYSTEM_PROMPT = """You are a PII detection classifier.
Analyse the input text and identify any personally identifiable information.
Categories to detect: name, email, phone, address, credit_card, ssn,
passport, aadhaar, pan, bank_account, date_of_birth, ip_address, password.

Respond ONLY with valid JSON in this exact format:
{
  "pii_detected": true or false,
  "confidence": float between 0.0 and 1.0,
  "categories_found": ["list", "of", "categories"]
}

Examples:
Input: "My email is john@example.com please reply"
Output: {"pii_detected": true, "confidence": 0.98, "categories_found": ["email"]}

Input: "What is the capital of France?"
Output: {"pii_detected": false, "confidence": 0.99, "categories_found": []}

Input: "Call me on 9876543210 or my SSN is 123-45-6789"
Output: {"pii_detected": true, "confidence": 0.97, "categories_found": ["phone", "ssn"]}"""

SAFE_DEFAULT = {"pii_detected": False, "confidence": 0.0, "categories_found": []}


def detect_pii(prompt_text: str) -> dict:
    client = get_openai_client()
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ],
        temperature=0.0,
        max_tokens=100,
    )

    text = response.choices[0].message.content
    if text is None:
        logging.warning("pii_detector: OpenAI response content was None")
        return dict(SAFE_DEFAULT)
    text = text.strip().removeprefix("```json").removesuffix("```").strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        logging.warning("pii_detector: failed to parse OpenAI response as JSON")
        return dict(SAFE_DEFAULT)

    if not isinstance(result, dict) or "pii_detected" not in result:
        logging.warning("pii_detector: OpenAI response missing expected keys")
        return dict(SAFE_DEFAULT)

    try:
        return {
            "pii_detected": bool(result.get("pii_detected", False)),
            "confidence": float(result.get("confidence", 0.0)),
            "categories_found": list(result.get("categories_found", [])),
        }
    except (ValueError, TypeError):
        logging.warning("pii_detector: OpenAI response had malformed field values")
        return dict(SAFE_DEFAULT)
