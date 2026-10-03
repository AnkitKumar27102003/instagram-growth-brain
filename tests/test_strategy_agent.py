
import pytest

from src.agents.strategy_agent import validate_topic_is_new
from src.models.strategy import StrategyOutput


def make_strategy(topic: str) -> StrategyOutput:
    return StrategyOutput.model_construct(topic=topic)


def test_rejects_exact_duplicate_topic():
    strategy = make_strategy("Why is the rupee weakening?")
    recent_topics = ["Why is the rupee weakening?"]

    with pytest.raises(ValueError, match="repeats a recently covered topic"):
        validate_topic_is_new(strategy, recent_topics)


def test_rejects_duplicate_with_different_case_and_spacing():
    strategy = make_strategy("  WHY IS THE RUPEE WEAKENING? ")
    recent_topics = ["why is the rupee weakening?"]

    with pytest.raises(ValueError, match="repeats a recently covered topic"):
        validate_topic_is_new(strategy, recent_topics)


def test_allows_a_new_topic():
    strategy = make_strategy("How does inflation affect households?")
    recent_topics = ["Why is the rupee weakening?"]

    validate_topic_is_new(strategy, recent_topics)