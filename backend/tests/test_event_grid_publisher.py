import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alerting.event_grid_publisher import publish_event


def test_publish_event_skips_when_topic_env_vars_not_set(monkeypatch):
    monkeypatch.delenv("AZURE_EVENT_GRID_TOPIC_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_EVENT_GRID_TOPIC_KEY", raising=False)
    publish_event({"event_id": "evt-1"})


def test_publish_event_posts_to_topic_when_configured(monkeypatch):
    posted = []

    class FakeResponse:
        def raise_for_status(self):
            pass

    def fake_post(url, headers, json, timeout):
        posted.append((url, headers, json))
        return FakeResponse()

    monkeypatch.setenv("AZURE_EVENT_GRID_TOPIC_ENDPOINT", "https://fake-topic.eastus-1.eventgrid.azure.net/api/events")
    monkeypatch.setenv("AZURE_EVENT_GRID_TOPIC_KEY", "fake-key")

    import alerting.event_grid_publisher as publisher_module
    monkeypatch.setattr(publisher_module.requests, "post", fake_post)

    publish_event({"event_id": "evt-1"})

    assert len(posted) == 1
    url, headers, body = posted[0]
    assert headers["aeg-sas-key"] == "fake-key"
    assert body[0]["data"]["event_id"] == "evt-1"
