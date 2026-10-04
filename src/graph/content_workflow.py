
from src.agents.critic_agent import (
    calculate_overall_score,
    critique_script,
)

from src.agents.research_agent import research_topic
from src.agents.strategy_agent import generate_strategy
from src.agents.verification_agent import verify_research

from src.agents.writer_agent import (
    generate_script,
    revise_script,
)

from src.agents.numeric_validation import (
    validate_script_numbers,
)

from src.memory.performance_memory import (
    save_approved_script,
)

from src.models.critique import CritiqueOutput
from src.models.research import ResearchOutput
from src.models.script import ScriptOutput
from src.models.strategy import StrategyOutput
from src.models.verification import VerificationOutput


PASSING_SCORE = 8.5
MAX_REVISION_ROUNDS = 3


def _apply_verification(
    research: ResearchOutput,
    verification: VerificationOutput,
) -> ResearchOutput:
    """
    Copy verification statuses onto matching research facts.

    The claim ID and claim text must match. If they do not,
    stop the workflow rather than applying an incorrect status.
    """
    verified_by_id = {
        item.claim_id: item
        for item in verification.claim_verifications
    }

    if len(verified_by_id) != len(research.key_facts):
        raise ValueError(
            "Verification count does not match research facts."
        )

    updated_facts = []

    for index, fact in enumerate(
        research.key_facts,
        start=1,
    ):
        claim_id = f"C{index}"
        result = verified_by_id.get(claim_id)

        if result is None:
            raise ValueError(
                f"Verification result missing for {claim_id}."
            )

        if result.claim.strip() != fact.claim.strip():
            raise ValueError(
                f"Verification does not match research fact "
                f"{claim_id}."
            )

        updated_facts.append(
            fact.model_copy(
                update={
                    "verification_status": result.status
                }
            )
        )

    return research.model_copy(
        update={
            "key_facts": updated_facts
        }
    )


def run_content_workflow(account_id: str) -> dict:
    """
    Run the complete NAZAR content generation workflow.

    Strategy -> Research -> Verification -> Writer
    -> Critic -> Revision -> Numeric Validation
    -> Approval -> Save
    """

    # Step 1: Generate content strategy
    strategy: StrategyOutput = generate_strategy(
        account_id
    )

    # Step 2: Research the selected topic
    research: ResearchOutput = research_topic(
        strategy
    )

    # Step 3: Verify the research claims
    verification: VerificationOutput = verify_research(
        research
    )

    # Step 4: Apply verification statuses to research facts
    verified_research = _apply_verification(
        research,
        verification,
    )

    # Step 5: Generate the initial script
    script: ScriptOutput = generate_script(
        strategy=strategy,
        research=verified_research,
    )

    # Track the highest-scoring script and critique
    best_script: ScriptOutput = script
    best_critique: CritiqueOutput | None = None
    best_score = 0.0

    revision_history = []
    revision_rounds = 0

    # Step 6: Critique and revise the script
    while True:
        critique: CritiqueOutput = critique_script(
            script=script,
            research=verified_research,
            verification=verification,
        )

        overall_score = calculate_overall_score(
            critique
        )

        revision_history.append(
            {
                "round": revision_rounds,
                "score": overall_score,
                "scores": critique.scores.model_dump(),
                "strengths": critique.strengths,
                "weaknesses": critique.weaknesses,
                "revision_instructions": (
                    critique.revision_instructions
                ),
            }
        )

        # Keep the highest-scoring version
        if overall_score > best_score:
            best_script = script
            best_critique = critique
            best_score = overall_score

        # Stop if the critic score reaches the threshold
        if overall_score >= PASSING_SCORE:
            break

        # Stop after the maximum revision rounds
        if revision_rounds >= MAX_REVISION_ROUNDS:
            break

        # Stop if there are no revision instructions
        if not critique.revision_instructions:
            break

        # Generate a revised script
        script = revise_script(
            strategy=strategy,
            research=verified_research,
            previous_script=script,
            revision_instructions=(
                critique.revision_instructions
            ),
        )

        revision_rounds += 1

    # Step 7: Select the best script and critique
    script = best_script
    critique = best_critique
    overall_score = best_score

    # Step 8: Check whether all research facts are supported
    facts_supported = all(
        fact.verification_status == "supported"
        for fact in verified_research.key_facts
    )

    # Step 9: Validate all numbers in the selected script
    numeric_validation = validate_script_numbers(
        script=script,
        research=verified_research,
    )

    # Step 10: Approve only if every condition is satisfied
    passed = (
        critique is not None
        and overall_score >= PASSING_SCORE
        and facts_supported
        and numeric_validation["passed"]
    )

    # Step 11: Save only approved scripts
    saved_script_id = None

    if passed:
        saved_script_id = save_approved_script(
            account_id=account_id,
            topic=script.topic,
            content_bucket=script.content_bucket,
            hook_style=script.hook_style,
            format=strategy.format,
            tone=strategy.tone,
            strategy=strategy.model_dump(),
            script_text="\n".join(
                segment.voiceover
                for segment in script.segments
            ),
            critic_score=overall_score,
        )

    # Step 12: Return the complete workflow result
    return {
        "strategy": strategy,
        "research": research,
        "verified_research": verified_research,
        "verification": verification,
        "script": script,
        "critique": critique,
        "overall_score": overall_score,
        "revision_rounds": revision_rounds,
        "passed": passed,
        "facts_supported": facts_supported,
        "numeric_validation": numeric_validation,
        "saved_script_id": saved_script_id,
        "revision_history": revision_history,
    }
