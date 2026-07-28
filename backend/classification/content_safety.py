import logging
import os

from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import AnalyzeTextOptions, TextCategory
from azure.core.credentials import AzureKeyCredential

SAFE_DEFAULT = {
    "harm_hate_score": 0,
    "harm_violence_score": 0,
    "harm_selfharm_score": 0,
    "harm_sexual_score": 0,
}

_CATEGORY_TO_FIELD = {
    TextCategory.HATE: "harm_hate_score",
    TextCategory.VIOLENCE: "harm_violence_score",
    TextCategory.SELF_HARM: "harm_selfharm_score",
    TextCategory.SEXUAL: "harm_sexual_score",
}


def _get_content_safety_client() -> ContentSafetyClient:
    endpoint = os.environ["AZURE_CONTENT_SAFETY_ENDPOINT"]
    key = os.environ["AZURE_CONTENT_SAFETY_KEY"]
    return ContentSafetyClient(endpoint, AzureKeyCredential(key))


def analyze_content_safety(prompt_text: str) -> dict:
    try:
        client = _get_content_safety_client()
        response = client.analyze_text(AnalyzeTextOptions(text=prompt_text))
    except Exception:
        logging.warning("content_safety: Analyze API call failed, returning safe default", exc_info=True)
        return dict(SAFE_DEFAULT)

    scores = dict(SAFE_DEFAULT)
    for item in response.categories_analysis:
        field = _CATEGORY_TO_FIELD.get(item.category)
        if field:
            scores[field] = item.severity or 0
    return scores
