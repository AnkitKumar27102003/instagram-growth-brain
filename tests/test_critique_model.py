
import pytest
from pydantic import ValidationError

from src.models.critique import CritiqueOutput


def make_critique(score=8.5):
    return {
        "scores": {
            "hook_strength": score,
            "emotional_arc": 8.0,
            "pacing": 7.5,
            "originality": 8.0,
            "nazar_alignment": 9.0,
        },
        "strengths": ["Clear opening hook"],
        "weaknesses": ["Pacing could be improved"],
        "revision_instructions": ["Shorten the middle section"],
    }


def test_valid_critique_is_accepted():
    critique = CritiqueOutput(**make_critique())

    assert critique.scores.hook_strength == 8.5
    assert critique.strengths == ["Clear opening hook"]


@pytest.mark.parametrize("score", [0.9, 10.1])
def test_invalid_score_is_rejected(score):
    with pytest.raises(ValidationError):
        CritiqueOutput(**make_critique(score))


def test_unexpected_field_is_rejected():
    data = make_critique()
    data["unexpected"] = "not allowed"

    with pytest.raises(ValidationError):
        CritiqueOutput(**data)
