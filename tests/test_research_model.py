
import pytest
from pydantic import ValidationError

from src.models.research import (
    ResearchFact,
    ResearchOutput,
    ResearchSource,
)


def valid_research():
    return {
        "topic": "Why oil prices affect India",
        "summary": "India imports crude oil, so international prices can affect domestic costs.",
        "key_facts": [
            {
                "claim": "India imports crude oil.",
                "evidence": "The supplied source reports India's crude oil import dependence.",
                "source_urls": ["https://example.com/oil"],
                "verification_status": "supported",
            }
        ],
        "context": ["International prices can affect import costs."],
        "sources": [
            {
                "title": "Oil Import Data",
                "url": "https://example.com/oil",
                "source_type": "Report",
            }
        ],
        "verification_notes": [],
    }


def test_valid_research_is_accepted():
    research = ResearchOutput.model_validate(valid_research())

    assert research.topic == "Why oil prices affect India"
    assert len(research.key_facts) == 1


def test_invalid_source_url_is_rejected():
    data = valid_research()
    data["sources"][0]["url"] = "not-a-url"

    with pytest.raises(ValidationError):
        ResearchOutput.model_validate(data)


def test_fact_with_missing_source_is_rejected():
    data = valid_research()
    data["key_facts"][0]["source_urls"] = [
        "https://unknown.example/fact"
    ]

    with pytest.raises(ValidationError, match="missing from sources"):
        ResearchOutput.model_validate(data)


def test_invalid_verification_status_is_rejected():
    data = valid_research()
    data["key_facts"][0]["verification_status"] = "verified_for_sure"

    with pytest.raises(ValidationError):
        ResearchOutput.model_validate(data)


def test_empty_key_facts_are_rejected():
    data = valid_research()
    data["key_facts"] = []

    with pytest.raises(ValidationError):
        ResearchOutput.model_validate(data)