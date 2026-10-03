
import json

from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from src.config import settings
from src.models.script import ScriptOutput
from src.models.strategy import StrategyOutput


SYSTEM_PROMPT = """
You are the Writer Agent for NAZAR, an Indian explainer and
documentary-style social media channel.

Write clear, natural Hinglish using simple Hindi and familiar
English words. Avoid difficult vocabulary and long sentences.

Create a concise Instagram Reel script based on the supplied
strategy. Keep the content factual, neutral, and non-partisan,
especially when discussing politics or geopolitics.

Do not invent statistics, quotes, events, or sources.
If a topic needs research, flag the need for verification in
the visual direction rather than making up facts.

Return only valid JSON matching the supplied schema.
Each segment's voiceover must contain exactly 18–23
whitespace-separated words.

Include:
- A strong opening hook
- A clear narrative progression
- A useful takeaway
- Visual directions for every segment

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


def generate_script(strategy: StrategyOutput) -> ScriptOutput:
    if not settings.openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    model = ChatOpenAI(
        model=settings.openrouter_model,
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.4,
    )

    schema = json.dumps(ScriptOutput.model_json_schema(), indent=2)

    prompt = f"""
{SYSTEM_PROMPT}

Required JSON schema:
{schema}

Selected strategy:
{strategy.model_dump_json(indent=2)}

Generate the script now.
"""

    last_error = None

    for attempt in range(2):
        try:
            response = model.invoke(prompt)
            data = _extract_json(response)
            return ScriptOutput.model_validate(data)

        except (json.JSONDecodeError, ValidationError, ValueError) as error:
            last_error = error

            if attempt == 0:
                prompt = f"""
{prompt}

Your previous response did not pass validation:
{str(error)}

Generate a corrected response. Return only valid JSON.
Make sure every voiceover contains 18–23 words.
"""

    raise ValueError(
        f"Writer Agent failed validation after 2 attempts: {last_error}"
    )

