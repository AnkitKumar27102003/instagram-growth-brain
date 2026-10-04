
from src.agents.critic_agent import (
    calculate_overall_score,
    critique_script,
)
from src.agents.numeric_validation import (
    validate_script_numbers,
)
from src.agents.research_agent import research_topic
from src.agents.script_verification_agent import verify_script
from src.agents.strategy_agent import generate_strategy
from src.agents.verification_agent import verify_research
from src.agents.writer_agent import (
    generate_script,
    revise_script,
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


def _log(message: str) -> None:
    """Print a consistent workflow log message."""
    print(f"[Content Workflow] {message}", flush=True)


def _run_stage(stage_name: str, function, *args, **kwargs):
    """
    Execute one workflow stage and log any exception.

    Re-raises exceptions so that unexpected failures are
    not silently treated as successful results.
    """
    _log(f"Starting: {stage_name}")

    try:
        result = function(*args, **kwargs)
        _log(f"Completed: {stage_name}")
        return result
    except Exception as error:
        _log(
            f"FAILED: {stage_name} | "
            f"{type(error).__name__}: {error}"
        )
        raise


def _apply_verification(
    research: ResearchOutput,
    verification: VerificationOutput,
) -> ResearchOutput:
    """
    Copy verification statuses onto matching research facts.

    Stop the workflow if the topic, claim count, claim IDs,
    or claim text does not match.
    """
    if (
        research.topic.strip().casefold()
        != verification.topic.strip().casefold()
    ):
        raise ValueError(
            "Verification topic does not match research."
        )

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
                    "verification_status": result.status,
                }
            )
        )

    return research.model_copy(
        update={
            "key_facts": updated_facts,
        }
    )


def run_content_workflow(account_id: str) -> dict:
    """
    Run the complete NAZAR content generation workflow.

    Strategy -> Research -> Verification -> Writer
    -> Critic -> Revision -> Numeric Validation
    -> Script Verification -> Approval -> Save

    A script is saved only if:
    - The critic score reaches the required threshold.
    - All research facts are supported.
    - Numeric validation passes.
    - Final script claims are supported by verified research.

    Each agent stage logs its start, completion, and failures.
    """

    _log("Starting NAZAR content generation workflow.")

    # Step 1: Generate content strategy
    strategy: StrategyOutput = _run_stage(
        "Strategy Agent",
        generate_strategy,
        account_id,
    )

    # Step 2: Research the selected topic
    research: ResearchOutput = _run_stage(
        "Research Agent",
        research_topic,
        strategy,
    )

    # Step 3: Verify the research claims
    verification: VerificationOutput = _run_stage(
        "Research Verification Agent",
        verify_research,
        research,
    )

    # Step 4: Apply verification statuses to research facts
    verified_research = _run_stage(
        "Apply Research Verification",
        _apply_verification,
        research,
        verification,
    )

    # Step 5: Generate the initial script
    script: ScriptOutput = _run_stage(
        "Writer Agent - Initial Script",
        generate_script,
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
        stage_name = (
            f"Critic Agent - Round {revision_rounds}"
        )

        critique: CritiqueOutput = _run_stage(
            stage_name,
            critique_script,
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

        _log(
            f"Critic round {revision_rounds} score: "
            f"{overall_score:.2f}/10"
        )

        # Keep the highest-scoring version
        if overall_score > best_score:
            best_script = script
            best_critique = critique
            best_score = overall_score

        # Stop if the critic score reaches the threshold
        if overall_score >= PASSING_SCORE:
            _log(
                f"Passing critic score reached: "
                f"{overall_score:.2f}/10"
            )
            break

        # Stop after the maximum revision rounds
        if revision_rounds >= MAX_REVISION_ROUNDS:
            _log(
                "Maximum revision rounds reached. "
                "Selecting the highest-scoring version."
            )
            break

        # Stop if there are no revision instructions
        if not critique.revision_instructions:
            _log(
                "No revision instructions returned. "
                "Stopping revision loop."
            )
            break

        # Generate a revised script
        next_round = revision_rounds + 1

        script = _run_stage(
            f"Writer Agent - Revision {next_round}",
            revise_script,
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

    if critique is None:
        raise RuntimeError(
            "Critic Agent did not produce a valid critique."
        )

    _log(
        f"Selected best script with score "
        f"{overall_score:.2f}/10."
    )

    # Step 8: Check whether all research facts are supported
    facts_supported = (
        bool(verified_research.key_facts)
        and all(
            fact.verification_status == "supported"
            for fact in verified_research.key_facts
        )
    )

    _log(
        "Research facts supported: "
        f"{facts_supported}"
    )

    # Step 9: Validate all numbers in the selected script
    numeric_validation = _run_stage(
        "Numeric Validation",
        validate_script_numbers,
        script=script,
        research=verified_research,
    )

    _log(
        "Numeric validation passed: "
        f"{numeric_validation.get('passed', False)}"
    )

    # Step 10: Verify factual claims in the final selected script
    script_verification = None
    script_verification_error = None

    try:
        script_verification = _run_stage(
            "Final Script Verification Agent",
            verify_script,
            script=script,
            research=verified_research,
        )
    except Exception as error:
        script_verification_error = (
            f"{type(error).__name__}: {error}"
        )
        _log(
            "Final Script Verification failed. "
            "The script will not be approved. "
            f"Reason: {script_verification_error}"
        )

    script_facts_supported = (
        script_verification is not None
        and script_verification.overall_status == "supported"
    )

    _log(
        "Final script facts supported: "
        f"{script_facts_supported}"
    )

    # Step 11: Approve only if every condition is satisfied
    passed = (
        critique is not None
        and overall_score >= PASSING_SCORE
        and facts_supported
        and numeric_validation.get("passed", False)
        and script_facts_supported
    )

    _log(f"Final approval status: {passed}")

    # Step 12: Save only approved scripts
    saved_script_id = None

    if passed:
        saved_script_id = _run_stage(
            "Save Approved Script",
            save_approved_script,
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
        _log(
            f"Approved script saved. ID: {saved_script_id}"
        )
    else:
        _log(
            "Script was not saved because one or more "
            "approval conditions were not met."
        )

    # Step 13: Return the complete workflow result
    result = {
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
        "script_verification": (
            script_verification.model_dump()
            if script_verification is not None
            else None
        ),
        "script_verification_error": script_verification_error,
        "script_facts_supported": script_facts_supported,
        "saved_script_id": saved_script_id,
        "revision_history": revision_history,
    }

    _log("Content workflow finished.")
    return result
