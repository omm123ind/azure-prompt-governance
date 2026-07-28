import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

KQL_DIR = Path(__file__).resolve().parents[2] / "infrastructure" / "kql-queries"

EXPECTED_QUERIES = {
    "flag-summary.kql": ["PromptAuditLog_CL", "action_taken_s", "ago("],
    "user-spend.kql": ["PromptAuditLog_CL", "cost_usd_d", "user_id_s", "ago("],
    "team-spend.kql": ["PromptAuditLog_CL", "cost_usd_d", "team_id_s", "ago("],
    "jailbreak-heatmap.kql": ["PromptAuditLog_CL", "jailbreak_score_d", "hourofday", "ago("],
    "pii-events.kql": ["PromptAuditLog_CL", "pii_detected_b", "ago("],
    "harm-by-category.kql": [
        "PromptAuditLog_CL", "harm_hate_score_d", "harm_violence_score_d",
        "harm_selfharm_score_d", "harm_sexual_score_d", "ago(",
    ],
    "anomaly-events.kql": ["PromptAuditLog_CL", 'action_taken_s == "anomaly"', "ago("],
    "audit-search.kql": ["PromptAuditLog_CL", "TimeGenerated between"],
}


def test_all_eight_kql_queries_exist():
    for filename in EXPECTED_QUERIES:
        assert (KQL_DIR / filename).exists(), f"missing {filename}"


def test_each_query_references_the_correct_table_and_required_fields():
    for filename, required_substrings in EXPECTED_QUERIES.items():
        content = (KQL_DIR / filename).read_text()
        for substring in required_substrings:
            assert substring in content, f"{filename} missing expected substring: {substring}"
