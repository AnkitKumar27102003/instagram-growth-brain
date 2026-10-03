
import pytest
from pydantic import ValidationError

from src.models.strategy import StrategyOutput


def valid_strategy():
    return {
        "topic": "Why oil prices affect India",
        "content_bucket": "Economy",
        "hook_style": "Curiosity",
        "format": "Documentary Reel",
        "tone": "Informative Hinglish",
        "rationale": "This topic connects global events to everyday costs.",
        "confidence": 0.9,
    }


def test_valid_strategy_is_accepted():
    strategy = StrategyOutput(**valid_strategy())

    assert strategy.topic == "Why oil prices affect India"
    assert strategy.confidence == 0.9
    assert strategy.avoid_topics == []


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_invalid_confidence_is_rejected(confidence):
    data = valid_strategy()
    data["confidence"] = confidence

    with pytest.raises(ValidationError):
        StrategyOutput(**data)


def test_unexpected_field_is_rejected():
    data = valid_strategy()
    data["made_up_field"] = "unexpected"

    with pytest.raises(ValidationError):
        StrategyOutput(**data)