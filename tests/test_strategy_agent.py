
import json
from types import SimpleNamespace

import pytest

from src import agents
from src.agents import strategy_agent
from src.models.strategy import StrategyOutput


def make_strategy(topic: str) -> StrategyOutput:
    return StrategyOutput.model_construct(topic=topic)


def make_strategy_response(topic: str) -> dict:
    """Create a complete, valid strategy response."""
    return {
        "topic": topic,
        "content_bucket": "Economy",
        "hook_style": "Curiosity",
        "format": "Documentary Reel",
        "tone": "Informative Hinglish",
        "rationale": (
            "This topic connects global events to everyday costs."
        ),
        "confidence": 0.9,
        "avoid_topics": ["Previously covered topics"],
        "avoid_formats": ["Interview"],
        "avoid_hook_styles": ["Generic question"],
    }


def setup_mocked_strategy_agent(monkeypatch, responses, recent_topics):
    """Mock memory and OpenRouter calls for strategy generation."""
    monkeypatch.setattr(
        strategy_agent.settings,
        "openrouter_api_key",
        "test-api-key",
    )

    recent_content = [
        {
            "topic": topic,
            "format": "Documentary Reel",
            "hook_style": "Curiosity",
        }
        for topic in recent_topics
    ]

    monkeypatch.setattr(
        strategy_agent,
        "get_recent_content",
        lambda account_id, limit: recent_content,
    )

    monkeypatch.setattr(
        strategy_agent,
        "get_performance_patterns",
        lambda account_id: {
            "patterns": [],
            "note": "Test performance data",
        },
    )

    class FakeModel:
        def __init__(self, response_list):
            self.responses = list(response_list)
            self.calls = []

        def invoke(self, messages):
            self.calls.append(messages)

            if not self.responses:
                raise AssertionError(
                    "The model was called more times than expected."
                )

            response = self.responses.pop(0)

            return SimpleNamespace(
                content=json.dumps(response)
            )

    fake_model = FakeModel(responses)

    monkeypatch.setattr(
        strategy_agent,
        "ChatOpenAI",
        lambda **kwargs: fake_model,
    )

    return fake_model


def test_rejects_exact_duplicate_topic():
    strategy = make_strategy("Why is the rupee weakening?")
    recent_topics = ["Why is the rupee weakening?"]

    with pytest.raises(
        ValueError,
        match="repeats a recently covered topic",
    ):
        strategy_agent.validate_topic_is_new(
            strategy,
            recent_topics,
        )


def test_rejects_duplicate_with_different_case_and_spacing():
    strategy = make_strategy(
        "  WHY IS THE RUPEE WEAKENING? "
    )
    recent_topics = ["why is the rupee weakening?"]

    with pytest.raises(
        ValueError,
        match="repeats a recently covered topic",
    ):
        strategy_agent.validate_topic_is_new(
            strategy,
            recent_topics,
        )


def test_allows_a_new_topic():
    strategy = make_strategy(
        "How does inflation affect households?"
    )
    recent_topics = ["Why is the rupee weakening?"]

    strategy_agent.validate_topic_is_new(
        strategy,
        recent_topics,
    )


def test_returns_new_topic_on_first_attempt(monkeypatch):
    fake_model = setup_mocked_strategy_agent(
        monkeypatch,
        responses=[
            make_strategy_response(
                "How does inflation affect households?"
            )
        ],
        recent_topics=[
            "Why is the rupee weakening?"
        ],
    )

    result = strategy_agent.generate_strategy(
        account_id="nazar.for.world"
    )

    assert result.topic == (
        "How does inflation affect households?"
    )
    assert len(fake_model.calls) == 1


def test_retries_after_duplicate_and_returns_new_topic(monkeypatch):
    fake_model = setup_mocked_strategy_agent(
        monkeypatch,
        responses=[
            make_strategy_response(
                "Why is the rupee weakening?"
            ),
            make_strategy_response(
                "How does inflation affect households?"
            ),
        ],
        recent_topics=[
            "Why is the rupee weakening?"
        ],
    )

    result = strategy_agent.generate_strategy(
        account_id="nazar.for.world"
    )

    assert result.topic == (
        "How does inflation affect households?"
    )
    assert len(fake_model.calls) == 2

    retry_prompt = fake_model.calls[1][1][1]

    assert "Why is the rupee weakening?" in retry_prompt
    assert "completely different topic" in retry_prompt


def test_retries_twice_before_returning_new_topic(monkeypatch):
    fake_model = setup_mocked_strategy_agent(
        monkeypatch,
        responses=[
            make_strategy_response(
                "Why is the rupee weakening?"
            ),
            make_strategy_response(
                "Why is the rupee weakening?"
            ),
            make_strategy_response(
                "How does inflation affect households?"
            ),
        ],
        recent_topics=[
            "Why is the rupee weakening?"
        ],
    )

    result = strategy_agent.generate_strategy(
        account_id="nazar.for.world"
    )

    assert result.topic == (
        "How does inflation affect households?"
    )
    assert len(fake_model.calls) == 3


def test_raises_error_after_three_duplicate_topics(monkeypatch):
    fake_model = setup_mocked_strategy_agent(
        monkeypatch,
        responses=[
            make_strategy_response(
                "Why is the rupee weakening?"
            ),
            make_strategy_response(
                "Why is the rupee weakening?"
            ),
            make_strategy_response(
                "Why is the rupee weakening?"
            ),
        ],
        recent_topics=[
            "Why is the rupee weakening?"
        ],
    )

    with pytest.raises(
        ValueError,
        match="Failed to generate a new topic after 3 attempts",
    ):
        strategy_agent.generate_strategy(
            account_id="nazar.for.world"
        )

    assert len(fake_model.calls) == 3