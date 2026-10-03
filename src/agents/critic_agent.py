
import json

from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from src.config import settings
from src.models.critique import CritiqueOutput
from src.models.script import ScriptOutput


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

Do not reward unsupported statistics or invented facts.
Flag claims that need independent verification.
Do not treat confident wording as evidence.

Provide specific strengths, weaknesses, and actionable
revision instructions. Avoid generic feedback.

Return only valid JSON matching the supplied schema.
Do not include Markdown fences or text outside the JSON.
"""


def _extract_json(response) -> dict:
    content = response.content

    if isinstance(content, list):
        content = "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict)
        )

    if not isinstance(content, str):
        raise ValueError("The model returned an unsupported response format.")

    content = content.strip()

    if content.startswith("```"):
        content = content.removeprefix("```json").removeprefix("```")
        content = content.removesuffix("```").strip()

    return json.loads(content)


def critique_script(script: ScriptOutput) -> CritiqueOutput:
    if not settings.openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    model = ChatOpenAI(
        model=settings.openrouter_model,
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.2,
    )

    schema = json.dumps(CritiqueOutput.model_json_schema(), indent=2)

    prompt = f"""
{SYSTEM_PROMPT}

Required JSON schema:
{schema}

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

        except (json.JSONDecodeError, ValidationError, ValueError) as error:
            last_error = error

            if attempt == 0:
                prompt = f"""
{prompt}

Your previous response failed validation:
{str(error)}

Return corrected JSON matching the schema exactly.
All five scores must be between 1 and 10.
"""

    raise ValueError(
        f"Critic Agent failed validation after 2 attempts: {last_error}"
    )


def calculate_overall_score(critique: CritiqueOutput) -> float:
    scores = critique.scores

    total = (
        scores.hook_strength
        + scores.emotional_arc
        + scores.pacing
        + scores.originality
        + scores.nazar_alignment
    )

    return round(total / 5, 2)