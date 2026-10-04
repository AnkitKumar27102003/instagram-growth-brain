
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

