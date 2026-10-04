
import json
from types import SimpleNamespace

import pytest
from src.agents import research_agent
from src.models.strategy import StrategyOutput


def make_strategy():
    return StrategyOutput(
        topic="Why oil prices affect India",
        content_bucket="Economy",
        hook_style="Curiosity",
        format="Documentary Reel",
        tone="Informative Hinglish",
        rationale="This topic connects international events to everyday costs.",
        confidence=0.9,
        avoid_topics=[],
        avoid_formats=[],
        avoid_hook_styles=[],
    )


def make_research_response(url="https://example.com/oil"):
    return {
        "topic": "Why oil prices affect India",
        "summary": "India imports crude oil, so international prices can affect domestic costs.",
        "key_facts": [
            {
                "claim": "India imports crude oil.",
                "evidence": "The search result reports India's crude oil import dependence.",
                "source_urls": [url],
                "verification_status": "supported",
            }
        ],
        "context": ["International prices can affect import costs."],
        "sources": [
            {
                "title": "Oil Import Data",
                "url": url,
                "source_type": "Report",
            }
        ],
        "verification_notes": [],
    }


def setup_mocks(monkeypatch, llm_response=None, search_results=None):
    monkeypatch.setattr(
        research_agent.settings,
        "openrouter_api_key",
        "test-key",
    )
    monkeypatch.setattr(
        research_agent.settings,
        "tavily_api_key",
        "test-tavily-key",
    )

    # Preserve an explicitly supplied empty list.
    results = (
        search_results
        if search_results is not None
        else [
            {
                "title": "Oil Import Data",
                "url": "https://example.com/oil",
                "content": "India's crude oil import dependence.",
            }
        ]
    )

    monkeypatch.setattr(
        research_agent,
        "_search_topic",
        lambda topic: results,
    )

    class FakeModel:
        def invoke(self, prompt):
            return SimpleNamespace(
                content=json.dumps(llm_response)
            )

    monkeypatch.setattr(
        research_agent,
        "ChatOpenAI",
        lambda **kwargs: FakeModel(),
    )


def test_research_topic_returns_valid_output(monkeypatch):
    setup_mocks(
        monkeypatch,
        llm_response=make_research_response(),
    )

    result = research_agent.research_topic(make_strategy())

    assert result.topic == "Why oil prices affect India"
    assert result.sources[0].url == "https://example.com/oil"


def test_research_rejects_url_not_in_search_results(monkeypatch):
    setup_mocks(
        monkeypatch,
        llm_response=make_research_response(
            "https://fake.example/unreturned"
        ),
    )

    with pytest.raises(ValueError, match="not returned by search"):
        research_agent.research_topic(make_strategy())


def test_research_rejects_empty_search_results(monkeypatch):
    setup_mocks(
        monkeypatch,
        llm_response=make_research_response(),
        search_results=[],
    )

    with pytest.raises(ValueError, match="No research results"):
        research_agent.research_topic(make_strategy())


def test_research_requires_openrouter_key(monkeypatch):
    monkeypatch.setattr(
        research_agent.settings,
        "openrouter_api_key",
        "",
    )

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        research_agent.research_topic(make_strategy())


def test_research_requires_tavily_key(monkeypatch):
    monkeypatch.setattr(
        research_agent.settings,
        "openrouter_api_key",
        "test-key",
    )
    monkeypatch.setattr(
        research_agent.settings,
        "tavily_api_key",
        "",
    )

    with pytest.raises(ValueError, match="TAVILY_API_KEY"):
        research_agent.research_topic(make_strategy())


def test_extract_json_handles_surrounding_text():
    response = SimpleNamespace(
        content='Here is the result:\n{"topic": "Oil"}\nDone.'
    )

    assert research_agent._extract_json(response) == {
        "topic": "Oil"
    }


def test_extract_json_handles_markdown_fence():
    response = SimpleNamespace(
        content='```json\n{"topic": "Oil"}\n```'
    )

    assert research_agent._extract_json(response) == {
        "topic": "Oil"
    }


def test_extract_json_rejects_invalid_json():
    response = SimpleNamespace(
        content='{"topic": "Oil",}'
    )

    with pytest.raises(ValueError, match="valid JSON object"):
        research_agent._extract_json(response)


def test_extract_json_rejects_non_object():
    response = SimpleNamespace(
        content='["oil", "economy"]'
    )

    with pytest.raises(ValueError):
        research_agent._extract_json(response)


def test_research_rejects_topic_mismatch(monkeypatch):
    data = make_research_response()
    data["topic"] = "A different topic"

    setup_mocks(monkeypatch, llm_response=data)

    with pytest.raises(
        ValueError,
        match="failed validation",
    ):
        research_agent.research_topic(make_strategy())


def test_research_retries_after_invalid_response(monkeypatch):
    setup_mocks(monkeypatch)

    valid_response = make_research_response()
    responses = [
        SimpleNamespace(content="not JSON"),
        SimpleNamespace(content=json.dumps(valid_response)),
    ]

    class FakeModel:
        def __init__(self):
            self.calls = 0

        def invoke(self, prompt):
            response = responses[self.calls]
            self.calls += 1
            return response

    fake_model = FakeModel()

    monkeypatch.setattr(
        research_agent,
        "ChatOpenAI",
        lambda **kwargs: fake_model,
    )

    result = research_agent.research_topic(make_strategy())

    assert result.topic == "Why oil prices affect India"
    assert fake_model.calls == 2


def test_research_provider_error_is_not_retried(monkeypatch):
    setup_mocks(monkeypatch)

    class FakeModel:
        calls = 0

        def invoke(self, prompt):
            self.calls += 1
            raise RuntimeError("Provider unavailable")

    fake_model = FakeModel()

    monkeypatch.setattr(
        research_agent,
        "ChatOpenAI",
        lambda **kwargs: fake_model,
    )

    with pytest.raises(RuntimeError, match="Provider unavailable"):
        research_agent.research_topic(make_strategy())

    assert fake_model.calls == 1
