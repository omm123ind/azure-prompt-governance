import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import MagicMock, patch

import pytest

from teams_notifier.function import post_to_teams


def test_post_to_teams_skips_when_webhook_url_not_set(monkeypatch):
    monkeypatch.delenv("TEAMS_WEBHOOK_URL", raising=False)
    with patch("teams_notifier.function.requests.post") as mock_post:
        post_to_teams({"event_id": "evt-1"})
        mock_post.assert_not_called()


def test_post_to_teams_posts_adaptive_card_to_webhook(monkeypatch):
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://example.com/webhook")
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    with patch("teams_notifier.function.requests.post", return_value=mock_response) as mock_post:
        event = {
            "event_id": "evt-1",
            "user_id": "hashed-user-1",
            "action_taken": "block",
            "block_reason": "pii_confidence_exceeded_threshold",
        }
        post_to_teams(event)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://example.com/webhook"
        card = kwargs["json"]
        assert "evt-1" in str(card)
        assert "hashed-user-1" in str(card)


def test_post_to_teams_raises_on_http_error(monkeypatch):
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://example.com/webhook")
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("boom")
    with patch("teams_notifier.function.requests.post", return_value=mock_response):
        with pytest.raises(Exception, match="boom"):
            post_to_teams({"event_id": "evt-1"})
