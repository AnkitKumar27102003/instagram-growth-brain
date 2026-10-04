
import json
from types import SimpleNamespace

import pytest

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
                    "Show an illustrative oil tanker, followed by "
                    "simple visuals of transport and household costs."
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
            self.prompts = []

        def invoke(self, prompt):
            self.prompts.append(prompt)
            response = responses[self.calls]
            self.calls += 1

            if isinstance(response, Exception):
                raise response

            if isinstance(response, str):
                content = response
            else:
                content = json.dumps(response)

            return SimpleNamespace(content=content)

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


def test_extract_json_handles_surrounding_text():
    response = SimpleNamespace(
        content='Result:\n{"topic": "Test"}\nFinished.'
    )

    result = writer_agent._extract_json(response)

    assert result["topic"] == "Test"


def test_extract_json_rejects_non_object():
    response = SimpleNamespace(
        content='["not", "an", "object"]'
    )

    with pytest.raises(ValueError, match="JSON object"):
        writer_agent._extract_json(response)


def test_extract_json_rejects_invalid_json():
    response = SimpleNamespace(
        content='{"topic": invalid}'
    )

    with pytest.raises(ValueError, match="invalid JSON|No valid JSON"):
        writer_agent._extract_json(response)


def test_extract_json_rejects_empty_response():
    response = SimpleNamespace(content=" ")

    with pytest.raises(ValueError, match="empty response"):
        writer_agent._extract_json(response)


def test_extract_json_rejects_unsupported_response():
    response = SimpleNamespace(content=None)

    with pytest.raises(
        ValueError,
        match="unsupported response format",
    ):
        writer_agent._extract_json(response)


def test_validate_script_removes_schema_metadata():
    data = make_valid_script()
    data["$defs"] = {
        "ScriptSegment": {"type": "object"}
    }
    data["$schema"] = (
        "https://json-schema.org/draft/2020-12/schema"
    )

    result = writer_agent._validate_script_output(
        data=data,
        expected_topic="Why oil prices affect India",
        output_label="Generated script",
        expected_content_bucket="Economy",
        expected_hook_style="Curiosity",
    )

    assert isinstance(result, ScriptOutput)


def test_generate_script_accepts_schema_metadata(monkeypatch):
    response = make_valid_script()
    response["$defs"] = {
        "ScriptSegment": {"type": "object"}
    }
    response["$schema"] = (
        "https://json-schema.org/draft/2020-12/schema"
    )

    fake_model = setup_model(monkeypatch, [response])

    result = writer_agent.generate_script(
        make_strategy(),
        make_research(),
    )

    assert isinstance(result, ScriptOutput)
    assert fake_model.calls == 1


def test_generate_script_retries_then_succeeds(monkeypatch):
    valid = make_valid_script()

    fake_model = setup_model(
        monkeypatch,
        ["Not JSON", valid],
    )

    result = writer_agent.generate_script(
        make_strategy(),
        make_research(),
    )

    assert isinstance(result, ScriptOutput)
    assert fake_model.calls == 2
    assert "failed validation" in fake_model.prompts[1].lower()


def test_generate_script_stops_after_three_invalid_responses(
    monkeypatch,
):
    fake_model = setup_model(
        monkeypatch,
        ["bad response", "still bad", "invalid again"],
    )

    with pytest.raises(
        ValueError,
        match="failed validation after 3 attempts",
    ):
        writer_agent.generate_script(
            make_strategy(),
            make_research(),
        )

    assert fake_model.calls == 3


def test_generate_script_rejects_topic_mismatch(monkeypatch):
    response = make_valid_script()
    response["topic"] = "Different topic"

    fake_model = setup_model(
        monkeypatch,
        [response, response, response],
    )

    with pytest.raises(
        ValueError,
        match="failed validation",
    ):
        writer_agent.generate_script(
            make_strategy(),
            make_research(),
        )

    assert fake_model.calls == 3


def test_generate_script_rejects_bucket_mismatch(monkeypatch):
    response = make_valid_script()
    response["content_bucket"] = "Politics"

    fake_model = setup_model(
        monkeypatch,
        [response, response, response],
    )

    with pytest.raises(
        ValueError,
        match="failed validation",
    ):
        writer_agent.generate_script(
            make_strategy(),
            make_research(),
        )

    assert fake_model.calls == 3


def test_generate_script_rejects_hook_style_mismatch(monkeypatch):
    response = make_valid_script()
    response["hook_style"] = "Shock"

    fake_model = setup_model(
        monkeypatch,
        [response, response, response],
    )

    with pytest.raises(
        ValueError,
        match="failed validation",
    ):
        writer_agent.generate_script(
            make_strategy(),
            make_research(),
        )

    assert fake_model.calls == 3


def test_generate_script_rejects_nonsequential_segments(monkeypatch):
    response = make_valid_script()
    second = dict(response["segments"][0])
    second["segment_number"] = 3
    response["segments"].append(second)

    fake_model = setup_model(
        monkeypatch,
        [response, response, response],
    )

    with pytest.raises(
        ValueError,
        match="failed validation",
    ):
        writer_agent.generate_script(
            make_strategy(),
            make_research(),
        )

    assert fake_model.calls == 3


def test_generate_script_requires_supported_facts(monkeypatch):
    research = make_research().model_copy(
        update={
            "key_facts": [
                {
                    "claim": "India imports crude oil.",
                    "evidence": "Unverified source excerpt.",
                    "source_urls": ["https://example.com/oil"],
                    "verification_status": "needs_verification",
                }
            ]
        }
    )

    with pytest.raises(
        ValueError,
        match="at least one key fact",
    ):
        writer_agent.generate_script(
            make_strategy(),
            research,
        )


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


def test_provider_error_is_not_retried(monkeypatch):
    fake_model = setup_model(
        monkeypatch,
        [RuntimeError("Provider unavailable")],
    )

    with pytest.raises(
        RuntimeError,
        match="Provider unavailable",
    ):
        writer_agent.generate_script(
            make_strategy(),
            make_research(),
        )

    assert fake_model.calls == 1


def test_revise_script_uses_critic_instructions(monkeypatch):
    valid = make_valid_script()
    fake_model = setup_model(monkeypatch, [valid])

    result = writer_agent.revise_script(
        strategy=make_strategy(),
        research=make_research(),
        previous_script=ScriptOutput.model_validate(valid),
        revision_instructions=["Make the hook more curious."],
    )

    assert isinstance(result, ScriptOutput)
    assert fake_model.calls == 1
    assert "Make the hook more curious." in fake_model.prompts[0]
