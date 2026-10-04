
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.agents import writer_agent
from src.models.research import ResearchOutput
from src.models.script import ScriptOutput
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


def make_research():
    return ResearchOutput(
        topic="Why oil prices affect India",
        summary=(
            "India imports crude oil, so international prices "
            "can affect domestic costs."
        ),
        key_facts=[
            {
                "claim": "India imports crude oil.",
                "evidence": (
                    "The research source reports India's crude oil "
                    "import dependence."
                ),
                "source_urls": ["https://example.com/oil"],
                "verification_status": "supported",
            }
        ],
        context=[
            "International prices can affect import costs."
        ],
        sources=[
            {
                "title": "Oil Import Data",
                "url": "https://example.com/oil",
                "source_type": "Report",
            }
        ],
        verification_notes=[],
    )


def make_valid_script():
    return {
        "topic": "Why oil prices affect India",
        "content_bucket": "Economy",
        "hook_style": "Curiosity",
        "segments": [
            {
                "segment_number": 1,
                "voiceover": (
                    "India imports much of its crude oil from abroad, "
                    "so global price changes can affect transport, "
                    "inflation, and everyday expenses for households."
                ),
                "visual_direction": (
                    "Show an oil tanker approaching India on a map, "
                    "followed by simple visuals of transport and prices."
                ),
            }
        ],
        "call_to_action": "Follow NAZAR for more explainers.",
    }


def setup_model(monkeypatch, responses):
    monkeypatch.setattr(
        writer_agent.settings,
        "openrouter_api_key",
        "test-key",
    )

    class FakeModel:
        def __init__(self):
            self.calls = 0

        def invoke(self, prompt):
            response = responses[self.calls]
            self.calls += 1
            return SimpleNamespace(
                content=json.dumps(response)
            )

    fake_model = FakeModel()

    monkeypatch.setattr(
        writer_agent,
        "ChatOpenAI",
        lambda **kwargs: fake_model,
    )

    return fake_model


def test_extract_json_parses_json():
    response = SimpleNamespace(
        content='{"topic": "Test", "segments": []}'
    )

    result = writer_agent._extract_json(response)

    assert result["topic"] == "Test"


def test_extract_json_handles_markdown_fence():
    response = SimpleNamespace(
        content='```json\n{"topic": "Test"}\n```'
    )

    result = writer_agent._extract_json(response)

    assert result["topic"] == "Test"


def test_extract_json_rejects_non_object():
    response = SimpleNamespace(
        content='["not", "an", "object"]'
    )

    with pytest.raises(
        ValueError,
        match="JSON object",
    ):
        writer_agent._extract_json(response)


def test_validate_script_removes_schema_metadata():
    data = make_valid_script()
    data["$defs"] = {
        "ScriptSegment": {
            "type": "object",
        }
    }
    data["$schema"] = (
        "https://json-schema.org/draft/2020-12/schema"
    )

    result = writer_agent._validate_script_output(
        data=data,
        expected_topic="Why oil prices affect India",
        output_label="Generated script",
    )

    assert isinstance(result, ScriptOutput)


def test_generate_script_accepts_schema_metadata(monkeypatch):
    response = make_valid_script()
    response["$defs"] = {
        "ScriptSegment": {
            "type": "object",
        }
    }
    response["$schema"] = (
        "https://json-schema.org/draft/2020-12/schema"
    )

    fake_model = setup_model(
        monkeypatch,
        [response],
    )

    result = writer_agent.generate_script(
        make_strategy(),
        make_research(),
    )

    assert isinstance(result, ScriptOutput)
    assert fake_model.calls == 1


def test_generate_script_rejects_topic_mismatch(monkeypatch):
    response = make_valid_script()
    response["topic"] = "Different topic"

    fake_model = setup_model(
        monkeypatch,
        [response, response],
    )

    with pytest.raises(
        ValueError,
        match="failed validation",
    ):
        writer_agent.generate_script(
            make_strategy(),
            make_research(),
        )

    assert fake_model.calls == 2


def test_generate_script_requires_api_key(monkeypatch):
    monkeypatch.setattr(
        writer_agent.settings,
        "openrouter_api_key",
        "",
    )

    with pytest.raises(
        ValueError,
        match="OPENROUTER_API_KEY",
    ):
        writer_agent.generate_script(
            make_strategy(),
            make_research(),
        )


def test_generate_script_rejects_research_topic_mismatch():
    strategy = make_strategy()
    research = make_research().model_copy(
        update={"topic": "Different topic"}
    )

    with pytest.raises(
        ValueError,
        match="Research topic does not match",
    ):
        writer_agent.generate_script(
            strategy,
            research,
        )
