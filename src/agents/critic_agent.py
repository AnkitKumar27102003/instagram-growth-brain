
import json

from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from src.config import settings
from src.models.critique import CritiqueOutput
from src.models.research import ResearchOutput
from src.models.script import ScriptOutput
from src.models.verification import VerificationOutput


SYSTEM_PROMPT = """
You are the Critic Agent for NAZAR, an Indian explainer
and documentary-style social media channel.

Evaluate the supplied Hinglish Reel script objectively
on five criteria, each scored from 1 to 10:

1. hook_strength: Does the opening create interest?
2. emotional_arc: Does the script sustain interest and
   deliver a meaningful payoff?
3. pacing: Is the flow concise and easy to follow?
4. originality: Does the script offer a distinct angle?
5. nazar_alignment: Is it clear, factual in tone,
   neutral, non-partisan, and aligned with NAZAR?

You will be provided with research and verification
results when available. Use these as the factual reference.

Verification rules:

- "supported": The claim was supported by the verifier.
  Do not label it unverified without a specific reason.
- "needs_verification": The claim has not been adequately
  verified. Do not treat it as an established fact.
- "contradicted": The evidence conflicts with the claim.
  Flag it as a factual problem.

A claim marked "supported" can still be used inaccurately
in the script. Check whether the script preserves the
claim's meaning, date, scope, units, and context.

Check whether statistics are clearly attributed and
whether the script avoids presenting correlations as
proven causation.

Do not assume a research fact appears in the script
unless the script actually uses it.

Do not reward unsupported statistics or invented facts.
Do not treat confident wording as evidence.

Evaluate the script on:
- Hook strength and curiosity
- Emotional arc and meaningful payoff
- Pacing and clarity
- Originality and distinct perspective
- Factual tone, neutrality, and NAZAR alignment
- Natural, understandable Hinglish
- Accuracy in the use of supplied research

Provide specific strengths, weaknesses, and actionable
revision instructions. Avoid generic feedback.

Revision instructions should be practical and specific.
If the script is weak, explain how to improve it without
inventing facts, statistics, examples, or human stories.

Return only valid JSON matching the supplied schema.
Do not include Markdown fences or text outside the JSON.
"""


def _extract_json(response) -> dict:
    """Extract a JSON object from the model response."""
    content = response.content

    if isinstance(content, list):
        text_parts = []

        for item in content:
            if isinstance(item, dict):
                text_parts.append(item.get("text", ""))
            elif isinstance(item, str):
                text_parts.append(item)

        content = "".join(text_parts)

    if not isinstance(content, str):
        raise ValueError(
            "The model returned an unsupported response format."
        )

    content = content.strip()

    if content.startswith("```"):
        content = content.removeprefix("```json")
        content = content.removeprefix("```")
        content = content.removesuffix("```").strip()

    data = json.loads(content)

    if not isinstance(data, dict):
        raise ValueError(
            "The model response must be a JSON object."
        )

    return data


def critique_script(
    script: ScriptOutput,
    research: ResearchOutput | None = None,
    verification: VerificationOutput | None = None,
) -> CritiqueOutput:
    """
    Critique a script using supplied research and verification
    context where available.

    research and verification are optional to preserve
    compatibility with existing tests or callers that
    only pass a script.
    """
    if not settings.openrouter_api_key:
        raise ValueError(
            "OPENROUTER_API_KEY is not configured."
        )

    model = ChatOpenAI(
        model=settings.openrouter_model,
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.2,
    )

    schema = json.dumps(
        CritiqueOutput.model_json_schema(),
        indent=2,
    )

    if research is not None:
        research_context = research.model_dump_json(
            indent=2
        )
    else:
        research_context = (
            "No research context was supplied. "
            "Be cautious with factual claims and "
            "flag claims that cannot be verified "
            "from the available information."
        )

    if verification is not None:
        verification_context = (
            verification.model_dump_json(indent=2)
        )
    else:
        verification_context = (
            "No verification results were supplied. "
            "Do not assume factual claims are verified."
        )

    prompt = f"""
{SYSTEM_PROMPT}

Required JSON schema:
{schema}

Research:
{research_context}

Verification results:
{verification_context}

Script to evaluate:
{script.model_dump_json(indent=2)}

Return your critique now.
"""

    last_error = None

    for attempt in range(2):
        try:
            response = model.invoke(prompt)
            data = _extract_json(response)

            return CritiqueOutput.model_validate(data)

        except (
            json.JSONDecodeError,
            ValidationError,
            ValueError,
        ) as error:
            last_error = error

            if attempt == 0:
                prompt = f"""
{prompt}

Your previous response failed validation:
{str(error)}

Return corrected JSON matching the schema exactly.

All five scores must be between 1 and 10.
All required fields must be present.
Do not include Markdown fences or explanations.
Return only valid JSON.
"""

    raise ValueError(
        "Critic Agent failed validation after 2 attempts: "
        f"{last_error}"
    )


def calculate_overall_score(
    critique: CritiqueOutput,
) -> float:
    """Calculate the average of the five critic scores."""
    scores = critique.scores

    total = (
        scores.hook_strength
        + scores.emotional_arc
        + scores.pacing
        + scores.originality
        + scores.nazar_alignment
    )

    return round(total / 5, 2)
