
import pytest

from src.agents.critic_agent import calculate_overall_score
from src.models.critique import CritiqueOutput


def make_critique(
    hook=8.0,
    emotional=9.0,
    pacing=7.0,
    originality=8.0,
    alignment=10.0,
):
    return CritiqueOutput(
        scores={
            "hook_strength": hook,
            "emotional_arc": emotional,
            "pacing": pacing,
            "originality": originality,
            "nazar_alignment": alignment,
        },
        strengths=["Clear narrative"],
        weaknesses=["Pacing could improve"],
        revision_instructions=["Tighten the middle"],
    )


def test_calculates_average_score():
    critique = make_critique()

    assert calculate_overall_score(critique) == 8.4


def test_calculates_perfect_score():
    critique = make_critique(
        hook=10,
        emotional=10,
        pacing=10,
        originality=10,
        alignment=10,
    )

    assert calculate_overall_score(critique) == 10.0


def test_calculates_lowest_valid_score():
    critique = make_critique(
        hook=1,
        emotional=1,
        pacing=1,
        originality=1,
        alignment=1,
    )

    assert calculate_overall_score(critique) == 1.0
