
from src.graph import content_workflow as workflow
from src.models.critique import CritiqueOutput
from src.models.script import ScriptOutput
from src.models.strategy import StrategyOutput


def make_strategy():
    return StrategyOutput(
        topic="India's digital economy",
        content_bucket="Economy",
        hook_style="Direct Question",
        format="Animated Explainer",
        tone="Informative Hinglish",
        rationale="Explain the topic using simple and factual language.",
        confidence=0.9,
    )


def make_script():
    return ScriptOutput(
        topic="India's digital economy",
        content_bucket="Economy",
        hook_style="Direct Question",
        segments=[
            {
                "segment_number": 1,
                "voiceover": " ".join(["India"] * 18),
                "visual_direction": "Show a map of India.",
            }
        ],
        call_to_action="Follow NAZAR for more explainers.",
    )


def make_critique(score):
    return CritiqueOutput(
        scores={
            "hook_strength": score,
            "emotional_arc": score,
            "pacing": score,
            "originality": score,
            "nazar_alignment": score,
        },
        strengths=["Clear explanation"],
        weaknesses=["Could be more engaging"],
        revision_instructions=["Improve the opening hook"],
    )


def setup_mocks(monkeypatch, critique_scores):
    strategy = make_strategy()
    script = make_script()
    critique_calls = {"count": 0}
    revision_calls = {"count": 0}

    monkeypatch.setattr(
        workflow,
        "generate_strategy",
        lambda account_id: strategy,
    )
    monkeypatch.setattr(
        workflow,
        "generate_script",
        lambda selected_strategy: script,
    )

    def fake_critique(selected_script):
        index = critique_calls["count"]
        critique_calls["count"] += 1
        return make_critique(critique_scores[index])

    def fake_revision(strategy, previous_script, revision_instructions):
        revision_calls["count"] += 1
        return previous_script

    monkeypatch.setattr(workflow, "critique_script", fake_critique)
    monkeypatch.setattr(workflow, "revise_script", fake_revision)

    return critique_calls, revision_calls


def test_workflow_stops_when_score_passes(monkeypatch):
    critique_calls, revision_calls = setup_mocks(
        monkeypatch,
        [9.0],
    )

    result = workflow.run_content_workflow("nazar.for.world")

    assert result["passed"] is True
    assert result["overall_score"] == 9.0
    assert result["revision_rounds"] == 0
    assert critique_calls["count"] == 1
    assert revision_calls["count"] == 0


def test_workflow_never_exceeds_three_revisions(monkeypatch):
    critique_calls, revision_calls = setup_mocks(
        monkeypatch,
        [6.0, 7.0, 7.5, 8.0],
    )

    result = workflow.run_content_workflow("nazar.for.world")

    assert result["passed"] is False
    assert result["revision_rounds"] == 3
    assert critique_calls["count"] == 4
    assert revision_calls["count"] == 3
    assert len(result["revision_history"]) == 4
