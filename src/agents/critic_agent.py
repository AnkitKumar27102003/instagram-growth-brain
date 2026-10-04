
import json

from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from src.config import settings
from src.models.critique import CritiqueOutput
from src.models.research import ResearchOutput
from src.models.script import ScriptOutput
from src.models.verification import VerificationOutput


MAX_CRITIC_ATTEMPTS = 2
MAX_PREVIOUS_RESPONSE_CHARS = 4000
MAX_ERROR_CHARS = 1500


SYSTEM_PROMPT = """
You are the Critic Agent for NAZAR, an Indian explainer
and documentary-style social media channel.

Evaluate the supplied Hinglish Reel script objectively
on five criteria, each scored from 1 to 10:

1. hook_strength: Does the opening create interest?
2. emotional_arc: Does the script sustain interest and
   deliver a meaningful payoff?
3. pacing: Is the script concise and easy to follow?
4. originality: Does it offer a distinct angle?
5. nazar_alignment: Is it factual in tone, neutral,
   non-partisan, and aligned with NAZAR?

Use supplied research and verification results as the
factual reference when available.

Verification rules:
- supported: The claim was supported by the verifier.
  Do not label it unverified without a specific reason.
- needs_verification: The claim has not been adequately
  verified. Do not treat it as an established fact.
- conflicting: The evidence conflicts with the claim.
  Flag it as a factual problem.

A supported claim can still be used inaccurately in the
script. Check whether the script preserves its meaning,
date, scope, units, and context.

Check whether statistics are clearly attributed and
whether the script avoids presenting correlations as
proven causation.

Do not assume a research fact appears in the script
unless the script actually uses it.

Do not reward unsupported statistics or invented facts.
Do not treat confident wording as evidence.

Evaluate:
- Hook strength and curiosity
- Emotional arc and meaningful payoff
- Pacing and clarity
- Originality and distinct perspective
- Factual tone, neutrality, and NAZAR alignment
- Natural, understandable Hinglish
- Accuracy in the use of supplied research

Provide specific strengths, weaknesses, and actionable
revision instructions. Avoid generic feedback.

Revision instructions must be practical and specific.
If the script is weak, explain how to improve it without
inventing facts, statistics, examples, or human stories.

Return only a valid JSON object matching the supplied
schema. Do not include Markdown fences or extra text.
"""


def _extract_json(response) -> dict:
    """
    Extract the first valid JSON object from a model response.

    Handles plain JSON, Markdown fences, surrounding text,
    and LangChain content blocks.
    """
    if isinstance(response, str):
        content = response
    else:
        content = getattr(response, "content", None)

    if isinstance(content, list):
        text_parts = []

        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    text_parts.append(text_value)
            else:
                text_value = getattr(item, "text", None)
                if isinstance(text_value, str):
                    text_parts.append(text_value)

        content = "\n".join(text_parts)

    if not isinstance(content, str):
        raise ValueError(
            "The model returned an unsupported response format."
        )

    content = content.strip()

    if not content:
        raise ValueError("The model returned an empty response.")

    decoder = json.JSONDecoder()

    # Try each opening brace, allowing JSON to be surrounded
    # by prose or Markdown fences.
    for index, character in enumerate(content):
        if character != "{":
            continue

        try:
            data, _ = decoder.raw_decode(content[index:])
        except json.JSONDecodeError:
            continue

        if isinstance(data, dict):
            return data

    raise ValueError(
        "No valid JSON object was found in the model response."
    )


def _build_prompt(
    script: ScriptOutput,
    research: ResearchOutput | None,
    verification: VerificationOutput | None,
) -> str:
    """Build the initial critic prompt with available context."""
    schema = json.dumps(
        CritiqueOutput.model_json_schema(),
        indent=2,
    )

    if research is not None:
        research_context = research.model_dump_json(indent=2)
    else:
        research_context = (
            "No research context was supplied. Be cautious "
            "with factual claims and flag claims that cannot "
            "be verified from the available information."
        )

    if verification is not None:
        verification_context = verification.model_dump_json(
            indent=2
        )
    else:
        verification_context = (
            "No verification results were supplied. "
            "Do not assume factual claims are verified."
        )

    return f"""
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


def _build_correction_prompt(
    original_prompt: str,
    error: Exception,
    previous_response: str,
) -> str:
    """Build a focused correction prompt after invalid output."""
    error_text = str(error)[:MAX_ERROR_CHARS]
    response_text = previous_response[
        :MAX_PREVIOUS_RESPONSE_CHARS
    ]

    return f"""
{original_prompt}

Your previous response was invalid.

Validation error:
{error_text}

Previous response:
{response_text}

Correct the response and return only one valid JSON object
matching the required schema.

Requirements:
- Include all required fields.
- Include all five scores.
- Each score must be a number between 1 and 10.
- strengths and weaknesses must each contain at least
  one specific item.
- revision_instructions must be practical and specific.
- Do not add fields outside the schema.
- Do not include Markdown fences or explanations.
"""


def critique_script(
    script: ScriptOutput,
    research: ResearchOutput | None = None,
    verification: VerificationOutput | None = None,
) -> CritiqueOutput:
    """
    Critique a script using supplied research and verification
    context where available.

    Makes at most two model attempts: an initial attempt and
    one corrective retry for invalid model output.

    Provider/API errors are allowed to propagate rather than
    being mistaken for response-validation errors.
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

    original_prompt = _build_prompt(
        script=script,
        research=research,
        verification=verification,
    )
    prompt = original_prompt
    last_error = None

    for attempt in range(MAX_CRITIC_ATTEMPTS):
        # Keep provider errors separate from parsing and schema
        # errors. This avoids an unnecessary retry on API errors.
        response = model.invoke(prompt)

        try:
            data = _extract_json(response)
            return CritiqueOutput.model_validate(data)

        except (ValueError, ValidationError) as error:
            last_error = error

            if attempt + 1 < MAX_CRITIC_ATTEMPTS:
                previous_response = getattr(
                    response, "content", ""
                )
                if not isinstance(previous_response, str):
                    previous_response = str(previous_response)

                prompt = _build_correction_prompt(
                    original_prompt=original_prompt,
                    error=error,
                    previous_response=previous_response,
                )

    raise ValueError(
        f"Critic Agent failed validation after "
        f"{MAX_CRITIC_ATTEMPTS} attempts: {last_error}"
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
