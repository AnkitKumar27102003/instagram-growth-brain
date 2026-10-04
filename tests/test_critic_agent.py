
import json
from types import SimpleNamespace

import pytest

from src.agents.critic_agent import (
    _extract_json,
    calculate_overall_score,
)
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


def valid_critique_data():
    return {
        "scores": {
            "hook_strength": 8,
            "emotional_arc": 9,
            "pacing": 7,
            "originality": 8,
            "nazar_alignment": 10,
        },
        "strengths": ["Clear narrative"],
        "weaknesses": ["Pacing could improve"],
        "revision_instructions": ["Tighten the middle"],
    }


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


def test_extracts_plain_json():
    expected = valid_critique_data()
    response = SimpleNamespace(
        content=json.dumps(expected)
    )

    assert _extract_json(response) == expected


def test_extracts_json_from_markdown_fence():
    expected = valid_critique_data()
    response = SimpleNamespace(
        content=f"```json\n{json.dumps(expected)}\n```"
    )

    assert _extract_json(response) == expected


def test_extracts_json_with_surrounding_text():
    expected = valid_critique_data()
    response = SimpleNamespace(
        content=(
            "Here is the critique:\n"
            f"{json.dumps(expected)}\n"
            "End of response."
        )
    )

    assert _extract_json(response) == expected


def test_extracts_json_from_content_blocks():
    expected = valid_critique_data()
    response = SimpleNamespace(
        content=[
            {"type": "text", "text": json.dumps(expected)}
        ]
    )

    assert _extract_json(response) == expected


def test_extract_json_rejects_non_object():
    response = SimpleNamespace(content='["not", "an", "object"]')

    with pytest.raises(
        ValueError,
        match="No valid JSON object",
    ):
        _extract_json(response)


def test_extract_json_rejects_invalid_json():
    response = SimpleNamespace(
        content='{"scores": invalid json}'
    )

    with pytest.raises(
        ValueError,
        match="No valid JSON object",
    ):
        _extract_json(response)


def test_extract_json_rejects_empty_response():
    response = SimpleNamespace(content="   ")

    with pytest.raises(
        ValueError,
        match="empty response",
    ):
        _extract_json(response)


def test_extract_json_rejects_unsupported_content():
    response = SimpleNamespace(content=None)

    with pytest.raises(
        ValueError,
        match="unsupported response format",
    ):
        _extract_json(response)
