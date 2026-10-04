
from src.graph import content_workflow as workflow

from src.models.critique import CritiqueOutput
from src.models.research import ResearchOutput
from src.models.script import ScriptOutput
from src.models.strategy import StrategyOutput
from src.models.verification import (
    ClaimVerification,
    EvidenceAssessment,
    VerificationOutput,
)


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


def make_research():
    return ResearchOutput(
        topic="India's digital economy",
        summary=(
            "India's digital economy includes digital payments, "
            "online services and technology-enabled businesses."
        ),
        key_facts=[
            {
                "claim": "Digital payments are part of India's digital economy.",
                "evidence": (
                    "The supplied source describes digital payments "
                    "as a component of the digital economy."
                ),
                "source_urls": [
                    "https://example.com/digital-economy"
                ],
                "verification_status": "supported",
            }
        ],
        context=[
            "Digital services influence commerce and daily activities."
        ],
        sources=[
            {
                "title": "Digital Economy Overview",
                "url": "https://example.com/digital-economy",
                "source_type": "Report",
            }
        ],
        verification_notes=[],
    )


def make_verification(research, status="supported"):
    verifications = []

    for index, fact in enumerate(research.key_facts, start=1):
        evidence = []

        if status == "supported":
            evidence = [
                EvidenceAssessment(
                    source_title="Verification source",
                    source_url="https://example.com/verification",
                    evidence_excerpt="Evidence supports the claim.",
                    supports_claim=True,
                    relevance_note="Relevant supporting evidence.",
                )
            ]

        verifications.append(
            ClaimVerification(
                claim_id=f"C{index}",
                claim=fact.claim,
                status=status,
                confidence=0.9 if status == "supported" else 0.4,
                explanation="Verification test result.",
                evidence=evidence,
            )
        )

    return VerificationOutput(
        topic=research.topic,
        claim_verifications=verifications,
        overall_status=status,
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
    research = make_research()
    script = make_script()

    critique_calls = {"count": 0}
    revision_calls = {"count": 0}

    saved_scripts = []
    research_calls = []
    writer_calls = []
    revision_research = []

    monkeypatch.setattr(
        workflow,
        "generate_strategy",
        lambda account_id: strategy,
    )

    def fake_research(strategy):
        research_calls.append(strategy)
        return research

    monkeypatch.setattr(
        workflow,
        "research_topic",
        fake_research,
    )

    def fake_verification(research):
        return make_verification(research)

    monkeypatch.setattr(
        workflow,
        "verify_research",
        fake_verification,
    )

    # Parameter names match the keyword arguments
    # passed by run_content_workflow().
    def fake_generate_script(strategy, research):
        writer_calls.append((strategy, research))
        return script

    monkeypatch.setattr(
        workflow,
        "generate_script",
        fake_generate_script,
    )

    # Accept the script and optional verified context
    # passed by the updated Critic Agent integration.
    def fake_critique(
        script,
        research=None,
        verification=None,
    ):
        index = critique_calls["count"]
        critique_calls["count"] += 1
        return make_critique(critique_scores[index])

    def fake_revision(
        strategy,
        research,
        previous_script,
        revision_instructions,
    ):
        revision_calls["count"] += 1
        revision_research.append(research)
        return previous_script

    def fake_save(**kwargs):
        saved_scripts.append(kwargs)
        return "test-script-id"

    monkeypatch.setattr(
        workflow,
        "critique_script",
        fake_critique,
    )

    monkeypatch.setattr(
        workflow,
        "revise_script",
        fake_revision,
    )

    monkeypatch.setattr(
        workflow,
        "save_approved_script",
        fake_save,
    )

    return (
        critique_calls,
        revision_calls,
        saved_scripts,
        research,
        research_calls,
        writer_calls,
        revision_research,
    )


def test_workflow_stops_when_score_passes(monkeypatch):
    (
        critique_calls,
        revision_calls,
        saved_scripts,
        research,
        research_calls,
        writer_calls,
        revision_research,
    ) = setup_mocks(monkeypatch, [9.0])

    result = workflow.run_content_workflow("nazar.for.world")

    assert result["passed"] is True
    assert result["overall_score"] == 9.0
    assert result["revision_rounds"] == 0
    assert critique_calls["count"] == 1
    assert revision_calls["count"] == 0

    assert len(research_calls) == 1
    assert research_calls[0] == result["strategy"]

    assert len(writer_calls) == 1
    assert writer_calls[0][0] == result["strategy"]
    assert writer_calls[0][1] == research

    assert result["research"] == research

    assert len(saved_scripts) == 1
    assert saved_scripts[0]["critic_score"] == 9.0
    assert result["saved_script_id"] == "test-script-id"


def test_workflow_never_exceeds_three_revisions(monkeypatch):
    (
        critique_calls,
        revision_calls,
        saved_scripts,
        research,
        research_calls,
        writer_calls,
        revision_research,
    ) = setup_mocks(
        monkeypatch,
        [6.0, 7.0, 7.5, 8.0],
    )

    result = workflow.run_content_workflow("nazar.for.world")

    assert result["passed"] is False
    assert result["revision_rounds"] == 3
    assert critique_calls["count"] == 4
    assert revision_calls["count"] == 3
    assert len(result["revision_history"]) == 4

    assert len(research_calls) == 1
    assert len(writer_calls) == 1
    assert revision_research == [research, research, research]
    assert result["research"] == research

    assert len(saved_scripts) == 0
    assert result["saved_script_id"] is None


def test_workflow_saves_script_at_exact_passing_threshold(monkeypatch):
    (
        _,
        _,
        saved_scripts,
        research,
        research_calls,
        writer_calls,
        _,
    ) = setup_mocks(
        monkeypatch,
        [8.5],
    )

    result = workflow.run_content_workflow("nazar.for.world")

    assert result["passed"] is True
    assert result["overall_score"] == 8.5

    assert len(research_calls) == 1
    assert len(writer_calls) == 1
    assert result["research"] == research

    assert len(saved_scripts) == 1
    assert saved_scripts[0]["topic"] == "India's digital economy"
    assert saved_scripts[0]["account_id"] == "nazar.for.world"
    assert result["saved_script_id"] == "test-script-id"


def test_workflow_does_not_save_script_below_threshold(monkeypatch):
    (
        critique_calls,
        revision_calls,
        saved_scripts,
        research,
        research_calls,
        writer_calls,
        revision_research,
    ) = setup_mocks(
        monkeypatch,
        [8.4, 8.4, 8.4, 8.4],
    )

    result = workflow.run_content_workflow("nazar.for.world")

    assert result["passed"] is False
    assert result["overall_score"] == 8.4
    assert result["revision_rounds"] == 3
    assert critique_calls["count"] == 4
    assert revision_calls["count"] == 3

    assert len(research_calls) == 1
    assert len(writer_calls) == 1
    assert revision_research == [research, research, research]
    assert result["research"] == research

    assert len(saved_scripts) == 0
    assert result["saved_script_id"] is None


def test_workflow_does_not_approve_unverified_claims(monkeypatch):
    (
        _,
        _,
        saved_scripts,
        research,
        research_calls,
        writer_calls,
        _,
    ) = setup_mocks(monkeypatch, [9.0])

    monkeypatch.setattr(
        workflow,
        "verify_research",
        lambda research: make_verification(
            research,
            status="needs_verification",
        ),
    )

    result = workflow.run_content_workflow("nazar.for.world")

    assert result["overall_score"] == 9.0
    assert result["facts_supported"] is False
    assert result["passed"] is False
    assert result["verification"].overall_status == "needs_verification"

    assert (
        result["verified_research"].key_facts[0].verification_status
        == "needs_verification"
    )

    assert len(writer_calls) == 1
    assert len(saved_scripts) == 0
    assert result["saved_script_id"] is None
