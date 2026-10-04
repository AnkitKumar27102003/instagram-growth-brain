
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.agents import strategy_agent
from src.models.strategy import StrategyOutput


def make_strategy(
    topic="Why oil prices affect India",
):
    return StrategyOutput(
        topic=topic,
        content_bucket="Economy",
        hook_style="Curiosity",
        format="Documentary Reel",
        tone="Informative Hinglish",
        rationale=(
            "This topic connects international events "
            "to everyday costs."
        ),
        confidence=0.9,
        avoid_topics=[],
        avoid_formats=[],
        avoid_hook_styles=[],
    )


def make_strategy_payload(
    topic="Why oil prices affect India",
):
    return make_strategy(topic).model_dump()


def make_fatigue_signals():
    return {
        "real": [],
        "simulated": [],
        "note": "Test fatigue signals",
    }


def make_breakout_signals():
    return {
        "real": {
            "baseline_engagement_rate": 0.0,
            "candidates": [],
            "successful_patterns": {},
        },
        "simulated": {
            "baseline_engagement_rate": 0.12,
            "candidates": [],
            "successful_patterns": {
                "hook_style": {"Curiosity": 2},
                "format": {"Documentary Reel": 1},
                "content_bucket": {"Economy": 2},
            },
        },
        "note": "Test breakout signals",
    }


def setup_mocks(
    monkeypatch,
    responses=None,
    recent_content=None,
    performance=None,
    fatigue=None,
    breakout=None,
):
    """Set up isolated memory and model mocks."""
    monkeypatch.setattr(
        strategy_agent.settings,
        "openrouter_api_key",
        "test-key",
    )
    monkeypatch.setattr(
        strategy_agent.settings,
        "openrouter_model",
        "test-model",
    )

    monkeypatch.setattr(
        strategy_agent,
        "get_recent_content",
        lambda account_id, limit=10: (
            recent_content if recent_content is not None else []
        ),
    )

    monkeypatch.setattr(
        strategy_agent,
        "get_performance_patterns",
        lambda account_id: (
            performance
            if performance is not None
            else {
                "patterns": [],
                "note": "No historical performance data.",
            }
        ),
    )

    monkeypatch.setattr(
        strategy_agent,
        "detect_feedback_topic_fatigue",
        lambda account_id: (
            fatigue if fatigue is not None else make_fatigue_signals()
        ),
    )

    monkeypatch.setattr(
        strategy_agent,
        "detect_breakout_content",
        lambda account_id: (
            breakout
            if breakout is not None
            else make_breakout_signals()
        ),
    )

    response_list = (
        responses
        if responses is not None
        else [make_strategy_payload()]
    )
    model_calls = []

    class FakeModel:
        def invoke(self, messages):
            model_calls.append(messages)
            response_index = min(
                len(model_calls) - 1,
                len(response_list) - 1,
            )
            response = response_list[response_index]

            if isinstance(response, Exception):
                raise response

            if isinstance(response, dict):
                response = json.dumps(response)

            return SimpleNamespace(content=response)

    monkeypatch.setattr(
        strategy_agent,
        "ChatOpenAI",
        lambda **kwargs: FakeModel(),
    )

    return model_calls


def test_rejects_exact_duplicate_topic():
    strategy = make_strategy(
        "Why oil prices affect India"
    )

    with pytest.raises(ValueError, match="repeats"):
        strategy_agent.validate_topic_is_new(
            strategy,
            ["Why oil prices affect India"],
        )


def test_rejects_duplicate_with_different_case_and_spacing():
    strategy = make_strategy(
        "  WHY OIL PRICES AFFECT INDIA! "
    )

    with pytest.raises(ValueError, match="repeats"):
        strategy_agent.validate_topic_is_new(
            strategy,
            ["why oil prices affect india"],
        )


def test_rejects_semantically_similar_topic(monkeypatch):
    monkeypatch.setattr(
        strategy_agent,
        "are_topics_semantically_similar",
        lambda topic_a, topic_b: True,
    )

    strategy = make_strategy(
        "Why crude oil prices affect Indian households"
    )

    with pytest.raises(ValueError, match="semantically similar"):
        strategy_agent.validate_topic_is_new(
            strategy,
            ["Why oil prices affect India"],
        )


def test_allows_a_new_topic(monkeypatch):
    monkeypatch.setattr(
        strategy_agent,
        "are_topics_semantically_similar",
        lambda topic_a, topic_b: False,
    )

    strategy = make_strategy("How India's UPI system works")

    strategy_agent.validate_topic_is_new(
        strategy,
        ["Why oil prices affect India"],
    )


def test_returns_new_topic_on_first_attempt(monkeypatch):
    setup_mocks(
        monkeypatch,
        responses=[
            make_strategy_payload(
                "How India's UPI system works"
            )
        ],
    )

    result = strategy_agent.generate_strategy(
        "nazar.for.world"
    )

    assert result.topic == "How India's UPI system works"


def test_retries_after_duplicate_and_returns_new_topic(monkeypatch):
    setup_mocks(
        monkeypatch,
        responses=[
            make_strategy_payload(
                "Why oil prices affect India"
            ),
            make_strategy_payload(
                "How India's UPI system works"
            ),
        ],
        recent_content=[
            {
                "topic": "Why oil prices affect India",
                "format": "Documentary Reel",
                "hook_style": "Curiosity",
            }
        ],
    )

    monkeypatch.setattr(
        strategy_agent,
        "are_topics_semantically_similar",
        lambda topic_a, topic_b: False,
    )

    result = strategy_agent.generate_strategy(
        "nazar.for.world"
    )

    assert result.topic == "How India's UPI system works"


def test_retries_twice_before_returning_new_topic(monkeypatch):
    setup_mocks(
        monkeypatch,
        responses=[
            make_strategy_payload("Topic one"),
            make_strategy_payload("Topic two"),
            make_strategy_payload("Topic three"),
        ],
        recent_content=[
            {
                "topic": "Topic one",
                "format": "Documentary Reel",
                "hook_style": "Curiosity",
            },
            {
                "topic": "Topic two",
                "format": "Animated Explainer",
                "hook_style": "Question",
            },
        ],
    )

    monkeypatch.setattr(
        strategy_agent,
        "are_topics_semantically_similar",
        lambda topic_a, topic_b: False,
    )

    result = strategy_agent.generate_strategy(
        "nazar.for.world"
    )

    assert result.topic == "Topic three"


def test_raises_error_after_three_duplicate_topics(monkeypatch):
    setup_mocks(
        monkeypatch,
        responses=[
            make_strategy_payload("Repeated topic"),
            make_strategy_payload("Repeated topic"),
            make_strategy_payload("Repeated topic"),
        ],
        recent_content=[
            {
                "topic": "Repeated topic",
                "format": "Documentary Reel",
                "hook_style": "Curiosity",
            }
        ],
    )

    monkeypatch.setattr(
        strategy_agent,
        "are_topics_semantically_similar",
        lambda topic_a, topic_b: False,
    )

    with pytest.raises(
        ValueError,
        match="Failed to generate a new topic after 3 attempts",
    ):
        strategy_agent.generate_strategy(
            "nazar.for.world"
        )


def test_semantic_threshold_must_be_valid():
    with pytest.raises(
        ValueError,
        match="Similarity threshold must be between 0 and 1",
    ):
        strategy_agent.are_topics_semantically_similar(
            "Topic A",
            "Topic B",
            threshold=1.2,
        )


def test_topic_fatigue_signals_are_in_prompt(monkeypatch):
    fatigue = {
        "real": [
            {
                "topic": "Repeated agriculture topic",
                "fatigue_candidate": True,
            }
        ],
        "simulated": [],
        "note": "Real feedback fatigue warning",
    }

    model_calls = setup_mocks(
        monkeypatch,
        responses=[
            make_strategy_payload(
                "How India's UPI system works"
            )
        ],
        fatigue=fatigue,
    )

    strategy_agent.generate_strategy("nazar.for.world")

    human_prompt = model_calls[0][1][1]
    assert "topic_fatigue_signals" in human_prompt
    assert "Repeated agriculture topic" in human_prompt
    assert "Real feedback fatigue warning" in human_prompt


def test_breakout_signals_are_in_prompt(monkeypatch):
    breakout = make_breakout_signals()
    model_calls = setup_mocks(
        monkeypatch,
        responses=[
            make_strategy_payload(
                "How India's UPI system works"
            )
        ],
        breakout=breakout,
    )

    strategy_agent.generate_strategy("nazar.for.world")

    human_prompt = model_calls[0][1][1]
    assert "breakout_signals" in human_prompt
    assert "successful_patterns" in human_prompt
    assert "Curiosity" in human_prompt
    assert "Test breakout signals" in human_prompt


def test_performance_patterns_are_in_prompt(monkeypatch):
    performance = {
        "patterns": [
            {
                "topic": "UPI",
                "hook_style": "Curiosity",
                "format": "Documentary Reel",
                "feedback_type": "simulated",
            }
        ],
        "note": "Descriptive test patterns",
    }

    model_calls = setup_mocks(
        monkeypatch,
        performance=performance,
        responses=[
            make_strategy_payload(
                "How India's UPI system works"
            )
        ],
    )

    strategy_agent.generate_strategy("nazar.for.world")

    human_prompt = model_calls[0][1][1]
    assert "performance_patterns" in human_prompt
    assert "Descriptive test patterns" in human_prompt


def test_requires_api_key(monkeypatch):
    monkeypatch.setattr(
        strategy_agent.settings,
        "openrouter_api_key",
        "",
    )

    with pytest.raises(
        ValueError,
        match="OpenRouter API key is missing",
    ):
        strategy_agent.generate_strategy(
            "nazar.for.world"
        )


def test_requires_nonempty_account_id():
    with pytest.raises(
        ValueError,
        match="Account ID must not be empty",
    ):
        strategy_agent.generate_strategy(" ")


def test_parses_json_response():
    payload = make_strategy_payload(
        "How India's UPI system works"
    )

    result = strategy_agent._parse_strategy_response(
        json.dumps(payload)
    )

    assert result.topic == "How India's UPI system works"


def test_parses_markdown_fenced_json():
    payload = make_strategy_payload(
        "How India's UPI system works"
    )

    result = strategy_agent._parse_strategy_response(
        "```json\n"
        + json.dumps(payload)
        + "\n```"
    )

    assert result.topic == "How India's UPI system works"


def test_rejects_invalid_strategy_json():
    with pytest.raises(
        ValueError,
        match="did not return valid StrategyOutput JSON",
    ):
        strategy_agent._parse_strategy_response(
            '{"topic": "Missing required fields"}'
        )


def test_retries_after_invalid_json(monkeypatch):
    model_calls = setup_mocks(
        monkeypatch,
        responses=[
            "not valid json",
            make_strategy_payload(
                "How India's UPI system works"
            ),
        ],
    )

    result = strategy_agent.generate_strategy(
        "nazar.for.world"
    )

    assert result.topic == "How India's UPI system works"
    assert len(model_calls) == 2


def test_does_not_merge_real_and_simulated_breakout_signals(
    monkeypatch,
):
    breakout = {
        "real": {
            "baseline_engagement_rate": 0.08,
            "candidates": [
                {"topic": "Real breakout topic"}
            ],
            "successful_patterns": {
                "hook_style": {"Question": 1}
            },
        },
        "simulated": {
            "baseline_engagement_rate": 0.12,
            "candidates": [
                {"topic": "Simulated breakout topic"}
            ],
            "successful_patterns": {
                "hook_style": {"Curiosity": 2}
            },
        },
        "note": "Real and simulated data are separate.",
    }

    model_calls = setup_mocks(
        monkeypatch,
        breakout=breakout,
        responses=[
            make_strategy_payload(
                "How India's UPI system works"
            )
        ],
    )

    strategy_agent.generate_strategy("nazar.for.world")

    human_prompt = model_calls[0][1][1]
    context_start = human_prompt.index("Account context:")
    context_end = human_prompt.index(
        "Return ONLY one valid JSON object"
    )
    context = json.loads(
        human_prompt[
            context_start + len("Account context:\n"):
            context_end
        ].strip()
    )

    signals = context["breakout_signals"]
    assert signals["real"]["candidates"][0]["topic"] == (
        "Real breakout topic"
    )
    assert signals["simulated"]["candidates"][0]["topic"] == (
        "Simulated breakout topic"
    )
    assert signals["real"] is not signals["simulated"]
