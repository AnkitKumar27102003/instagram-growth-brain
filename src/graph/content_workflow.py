
from src.agents.critic_agent import (
    calculate_overall_score,
    critique_script,
)
from src.agents.strategy_agent import generate_strategy
from src.agents.writer_agent import (
    generate_script,
    revise_script,
)
from src.models.critique import CritiqueOutput
from src.models.script import ScriptOutput
from src.models.strategy import StrategyOutput


PASSING_SCORE = 8.5
MAX_REVISION_ROUNDS = 3


def run_content_workflow(account_id: str) -> dict:
    strategy: StrategyOutput = generate_strategy(account_id)
    script: ScriptOutput = generate_script(strategy)

    revision_history = []
    critique: CritiqueOutput | None = None
    overall_score = 0.0
    revision_rounds = 0

    while True:
        critique = critique_script(script)
        overall_score = calculate_overall_score(critique)

        revision_history.append({
            "round": revision_rounds,
            "score": overall_score,
            "scores": critique.scores.model_dump(),
            "strengths": critique.strengths,
            "weaknesses": critique.weaknesses,
            "revision_instructions": critique.revision_instructions,
        })

        if overall_score >= PASSING_SCORE:
            break

        if revision_rounds >= MAX_REVISION_ROUNDS:
            break

        if not critique.revision_instructions:
            break

        script = revise_script(
            strategy=strategy,
            previous_script=script,
            revision_instructions=critique.revision_instructions,
        )
        revision_rounds += 1

    return {
        "strategy": strategy,
        "script": script,
        "critique": critique,
        "overall_score": overall_score,
        "revision_rounds": revision_rounds,
        "passed": overall_score >= PASSING_SCORE,
        "revision_history": revision_history,
    }
