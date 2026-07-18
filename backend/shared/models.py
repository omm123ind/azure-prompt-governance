from typing import Optional
from pydantic import BaseModel


class AuditEvent(BaseModel):
    timestamp: Optional[str] = None
    event_id: str
    session_id: str
    user_id: str
    team_id: str
    prompt_hash: str
    response_hash: str
    pii_detected: bool
    pii_confidence: float
    pii_categories: list[str]
    jailbreak_score: float
    harm_hate_score: int
    harm_violence_score: int
    harm_selfharm_score: int
    harm_sexual_score: int
    action_taken: str
    block_reason: Optional[str] = None
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    model: str
    latency_ms: int


class ClassificationResult(BaseModel):
    pii_detected: bool
    pii_confidence: float
    pii_categories: list[str]
    jailbreak_score: float
    harm_hate_score: int
    harm_violence_score: int
    harm_selfharm_score: int
    harm_sexual_score: int
    classification_latency_ms: int
