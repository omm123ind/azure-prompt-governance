import json
import logging
import os

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.monitor.ingestion import LogsIngestionClient


def push_to_log_analytics(event_dict: dict) -> None:
    endpoint = os.environ["AZURE_DCE_LOGS_INGESTION_ENDPOINT"]
    rule_id = os.environ["AZURE_DCR_IMMUTABLE_ID"]
    stream_name = "Custom-PromptAuditLog"

    credential = DefaultAzureCredential()
    client = LogsIngestionClient(endpoint=endpoint, credential=credential)

    row = {
        "event_id_s": event_dict["event_id"],
        "session_id_s": event_dict["session_id"],
        "user_id_s": event_dict["user_id"],
        "team_id_s": event_dict["team_id"],
        "prompt_hash_s": event_dict["prompt_hash"],
        "response_hash_s": event_dict["response_hash"],
        "pii_detected_b": event_dict["pii_detected"],
        "pii_confidence_d": event_dict["pii_confidence"],
        "pii_categories_s": json.dumps(event_dict["pii_categories"]),
        "jailbreak_score_d": event_dict["jailbreak_score"],
        "harm_hate_score_d": event_dict["harm_hate_score"],
        "harm_violence_score_d": event_dict["harm_violence_score"],
        "harm_selfharm_score_d": event_dict["harm_selfharm_score"],
        "harm_sexual_score_d": event_dict["harm_sexual_score"],
        "action_taken_s": event_dict["action_taken"],
        "block_reason_s": event_dict.get("block_reason") or "",
        "prompt_tokens_d": event_dict["prompt_tokens"],
        "completion_tokens_d": event_dict["completion_tokens"],
        "cost_usd_d": event_dict["cost_usd"],
        "model_s": event_dict["model"],
        "latency_ms_d": event_dict["latency_ms"],
    }
    client.upload(rule_id=rule_id, stream_name=stream_name, logs=[row])


def main(event: func.EventHubEvent):
    body = event.get_body().decode("utf-8")
    event_dict = json.loads(body)
    logging.info("consuming audit event %s from Event Hub", event_dict.get("event_id"))
    push_to_log_analytics(event_dict)
