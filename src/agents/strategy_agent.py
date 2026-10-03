import json

from langchain_openai import ChatOpenAI

from src.config import settings
from src.memory.performance_memory import (
    get_performance_patterns,
    get_recent_content,
)
from src.models.strategy import StrategyOutput


SYSTEM_PROMPT = """
You are the Strategy Agent for NAZAR, an Indian
Hinglish explainer channel covering politics,
economy, history, geopolitics and current affairs.

Your job is to propose a content strategy using
the account's recent content and performance data.

Rules:
1. Do not repeat recently covered topics.
2. Rotate hook styles and formats where practical.
3. Use performance patterns as descriptive signals,
   not guarantees of future results.
4. Keep simulated and real performance separate.
   Never describe simulated data as real.
5. Do not invent events, statistics or sources.
6. For political topics, remain neutral, factual
   and nonpartisan. Do not advocate for political
   actors, parties or policy choices.
7. Prefer clear, simple Hinglish suitable for a
   broad Indian audience.
8. Explain why the proposed topic is relevant.
9. Include topics, formats and hooks to avoid.
10. Return only a valid JSON object matching the
    schema provided in the user message.
11. Do not include Markdown code fences or text
    outside the JSON object.
"""


def _normalize_topic(topic: str) -> str:
    """Normalize a topic for basic duplicate detection."""
    return " ".join(topic.casefold().split()).strip(" .!?,")


def validate_topic_is_new(
    strategy: StrategyOutput,
    recent_topics: list[str],
) -> None:
    """Reject a strategy that repeats a recently covered topic."""
    proposed_topic = _normalize_topic(strategy.topic)

    for recent_topic in recent_topics:
        if proposed_topic == _normalize_topic(recent_topic):
            raise ValueError(
                "The generated strategy repeats a recently "
                f"covered topic: {strategy.topic}"
            )


def generate_strategy(
    account_id: str,
    content_goal: str = "Recommend the next useful post for NAZAR.",
) -> StrategyOutput:
    """Generate a memory-aware strategy using OpenRouter."""

    if not settings.openrouter_api_key.strip():
        raise ValueError(
            "OpenRouter API key is missing. "
            "Check your .env configuration."
        )

    # Retrieve recent approved content from memory.
    recent_content = get_recent_content(
        account_id=account_id,
        limit=10,
    )

    # Retrieve historical performance patterns.
    performance = get_performance_patterns(account_id)

    # Build explicit avoidance lists from recent content.
    recent_topics = [
        item["topic"] for item in recent_content
    ]

    recent_formats = [
        item["format"] for item in recent_content
    ]

    recent_hooks = [
        item["hook_style"] for item in recent_content
    ]

    # Prepare context for the language model.
    context = {
        "account_id": account_id,
        "content_goal": content_goal,
        "recent_content": recent_content,
        "recent_topics_to_avoid": recent_topics,
        "recent_formats_to_rotate": recent_formats,
        "recent_hooks_to_rotate": recent_hooks,
        "performance_patterns": performance["patterns"],
        "performance_note": performance["note"],
    }

    # Configure OpenRouter using the OpenAI-compatible endpoint.
    model = ChatOpenAI(
        model=settings.openrouter_model,
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.3,
        max_retries=1,
    )

    # Give the model the expected Pydantic JSON schema.
    schema = json.dumps(
        StrategyOutput.model_json_schema(),
        ensure_ascii=False,
    )

    # Maximum number of strategy-generation attempts.
    # 1 initial attempt + 2 retries.
    max_attempts = 3

    # Stores the duplicate topic when a retry is required.
    duplicate_topic = None

    for attempt in range(max_attempts):

        # Build the normal generation request.
        human_prompt = (
            "Create a content strategy using this "
            "account context:\n"
            f"{json.dumps(context, ensure_ascii=False, indent=2)}"
            "\n\n"
            "Return ONLY one valid JSON object. "
            "Do not include Markdown fences, comments, "
            "or explanations outside the JSON.\n\n"
            "The JSON must follow this schema:\n"
            f"{schema}"
        )

        # If a previous attempt generated a duplicate topic,
        # explicitly ask for a completely different topic.
        if duplicate_topic is not None:
            human_prompt = (
                "Your previous response repeated a recently "
                "covered topic.\n\n"
                f"Rejected topic: {duplicate_topic}\n\n"
                "Generate a completely different topic this time. "
                "Do not use the same topic with different wording. "
                "Choose a genuinely distinct subject while following "
                "the original account context.\n\n"
                "Account context:\n"
                f"{json.dumps(context, ensure_ascii=False, indent=2)}"
                "\n\n"
                "Return ONLY one valid JSON object. "
                "Do not include Markdown fences, comments, "
                "or explanations outside the JSON.\n\n"
                "The JSON must follow this schema:\n"
                f"{schema}"
            )

        # Ask the model to generate the strategy.
        result = model.invoke(
            [
                ("system", SYSTEM_PROMPT),
                ("human", human_prompt),
            ]
        )

        # Extract the text returned by the model.
        content = result.content

        if isinstance(content, str):
            raw_text = content

        elif isinstance(content, list):
            text_parts = []

            for part in content:
                if isinstance(part, str):
                    text_parts.append(part)

                elif isinstance(part, dict):
                    text_value = part.get("text")

                    if isinstance(text_value, str):
                        text_parts.append(text_value)

            raw_text = "\n".join(text_parts)

        else:
            raise ValueError(
                "The model returned an unsupported response format."
            )

        raw_text = raw_text.strip()

        # Remove a Markdown code fence if the model adds one anyway.
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            raw_text = "\n".join(lines).strip()

            if raw_text.lower().startswith("json"):
                raw_text = raw_text[4:].strip()

        # Parse JSON and validate all fields using Pydantic.
        try:
            parsed_data = json.loads(raw_text)
            strategy = StrategyOutput.model_validate(parsed_data)

        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            raise ValueError(
                "The model did not return valid StrategyOutput JSON. "
                "Try again or select another OpenRouter model. "
                f"Parsing details: {exc}"
            ) from exc

        # Check whether the generated topic is a duplicate.
        try:
            validate_topic_is_new(
                strategy,
                recent_topics,
            )

        except ValueError as exc:
            duplicate_topic = strategy.topic

            # If this was the final allowed attempt,
            # stop instead of making another API call.
            if attempt == max_attempts - 1:
                raise ValueError(
                    f"Failed to generate a new topic after "
                    f"{max_attempts} attempts. "
                    f"Last duplicate topic: {strategy.topic}"
                ) from exc

            # Otherwise retry with duplicate-topic feedback.
            continue

        # Topic is new, so return the valid strategy.
        return strategy

    # Defensive fallback. The loop should always either
    # return a strategy or raise an exception.
    raise RuntimeError(
        "Strategy generation ended unexpectedly."
    )