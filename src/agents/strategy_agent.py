
import json
import re
from functools import lru_cache

from langchain_openai import ChatOpenAI
from pydantic import ValidationError
from sentence_transformers import SentenceTransformer

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
10. Return one JSON object containing only the
    fields required by the supplied schema.
11. Do not return the JSON schema itself.
12. Do not include Markdown code fences or text
    outside the JSON object.
13. Do not add extra fields such as title, type,
    properties, definitions or schema metadata.
"""


# Similarity threshold for flagging potentially
# duplicate topics. Tune with real topic examples.
SEMANTIC_SIMILARITY_THRESHOLD = 0.82

# Maximum attempts: 1 initial attempt + 2 retries.
MAX_STRATEGY_ATTEMPTS = 3


def _normalize_topic(topic: str) -> str:
    """Normalize a topic for exact duplicate detection."""
    return " ".join(topic.casefold().split()).strip(" .!?,")


@lru_cache(maxsize=1)
def _get_embedding_model():
    """Load and cache the local semantic embedding model."""
    return SentenceTransformer("all-MiniLM-L6-v2")


def are_topics_semantically_similar(
    topic_a: str,
    topic_b: str,
    threshold: float = SEMANTIC_SIMILARITY_THRESHOLD,
) -> bool:
    """
    Compare two topics using locally generated embeddings.

    Both embeddings are normalized, so their dot product
    represents cosine similarity.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(
            "Similarity threshold must be between 0 and 1."
        )

    normalized_a = _normalize_topic(topic_a)
    normalized_b = _normalize_topic(topic_b)

    if not normalized_a or not normalized_b:
        return False

    if normalized_a == normalized_b:
        return True

    model = _get_embedding_model()

    embeddings = model.encode(
        [topic_a, topic_b],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    similarity = float(embeddings[0] @ embeddings[1])

    return similarity >= threshold


def validate_topic_is_new(
    strategy: StrategyOutput,
    recent_topics: list[str],
) -> None:
    """Reject exact or semantically similar recent topics."""
    proposed_topic = strategy.topic

    for recent_topic in recent_topics:
        # First, check exact duplicates after normalization.
        if _normalize_topic(proposed_topic) == _normalize_topic(
            recent_topic
        ):
            raise ValueError(
                "The generated strategy repeats a recently "
                f"covered topic: {proposed_topic}"
            )

        # Then check for semantic similarity.
        if are_topics_semantically_similar(
            proposed_topic,
            recent_topic,
        ):
            raise ValueError(
                "The generated strategy is semantically similar "
                "to a recently covered topic: "
                f"{proposed_topic}"
            )


def _extract_response_text(content) -> str:
    """Extract text from supported model response formats."""
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        text_parts = []

        for part in content:
            if isinstance(part, str):
                text_parts.append(part)

            elif isinstance(part, dict):
                text_value = part.get("text")

                if isinstance(text_value, str):
                    text_parts.append(text_value)

        if text_parts:
            return "\n".join(text_parts).strip()

    raise ValueError(
        "The model returned an unsupported response format."
    )


def _clean_json_text(raw_text: str) -> str:
    """Remove Markdown fences and surrounding whitespace."""
    raw_text = raw_text.strip()

    if raw_text.startswith("```"):
        lines = raw_text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        raw_text = "\n".join(lines).strip()

        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:].strip()

    # If the model added explanatory text around the JSON,
    # attempt to isolate the JSON object.
    if not raw_text.startswith("{"):
        match = re.search(
            r"\{.*\}",
            raw_text,
            flags=re.DOTALL,
        )

        if match:
            raw_text = match.group(0).strip()

    return raw_text


def _unwrap_strategy_payload(parsed_data: dict) -> dict:
    """
    Unwrap common response envelopes while keeping the
    actual StrategyOutput validation strict.

    Does not remove unexpected fields from the strategy.
    """
    if not isinstance(parsed_data, dict):
        raise ValueError(
            "The model response must be a JSON object."
        )

    possible_wrappers = (
        "StrategyOutput",
        "strategy",
        "output",
        "data",
    )

    for wrapper in possible_wrappers:
        nested = parsed_data.get(wrapper)

        if isinstance(nested, dict):
            return nested

    return parsed_data


def _parse_strategy_response(raw_text: str) -> StrategyOutput:
    """Parse JSON and validate it using the Pydantic model."""
    cleaned_text = _clean_json_text(raw_text)

    try:
        parsed_data = json.loads(cleaned_text)

        if not isinstance(parsed_data, dict):
            raise ValueError(
                "The model response must be a JSON object."
            )

        parsed_data = _unwrap_strategy_payload(parsed_data)

        return StrategyOutput.model_validate(parsed_data)

    except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as exc:
        raise ValueError(
            "The model did not return valid StrategyOutput JSON. "
            "The response must contain only the fields defined "
            "by StrategyOutput. "
            f"Parsing details: {exc}"
        ) from exc


def _build_human_prompt(
    context: dict,
    schema: str,
    duplicate_topic: str | None = None,
    previous_error: str | None = None,
) -> str:
    """Build the generation or correction prompt."""
    if duplicate_topic is not None:
        instruction = (
            "Your previous response repeated a recently "
            "covered topic.\n\n"
            f"Rejected topic: {duplicate_topic}\n\n"
            "Generate a genuinely different topic. Do not use "
            "the same topic with different wording or cover "
            "the same underlying subject again. Choose a "
            "distinct subject while following the original "
            "account context.\n\n"
        )
    else:
        instruction = (
            "Create a content strategy using this account "
            "context.\n\n"
        )

    prompt = (
        f"{instruction}"
        "Account context:\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2)}"
        "\n\n"
        "Return ONLY one valid JSON object representing a "
        "StrategyOutput instance.\n"
        "Do not return the JSON schema itself.\n"
        "Do not include Markdown fences, comments, explanations, "
        "or extra fields outside the schema.\n\n"
        "The JSON must follow this schema:\n"
        f"{schema}\n\n"
        "The JSON must contain the actual strategy values, "
        "not schema metadata such as title, type, properties, "
        "or definitions."
    )

    if previous_error is not None:
        prompt += (
            "\n\nYour previous response failed validation:\n"
            f"{previous_error}\n\n"
            "Correct the response. Return a valid StrategyOutput "
            "JSON object with all required fields and no "
            "unexpected fields. Do not return the schema itself."
        )

    return prompt


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

    # Build avoidance lists from recent content.
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
        indent=2,
    )

    duplicate_topic = None
    previous_error = None

    for attempt in range(MAX_STRATEGY_ATTEMPTS):
        human_prompt = _build_human_prompt(
            context=context,
            schema=schema,
            duplicate_topic=duplicate_topic,
            previous_error=previous_error,
        )

        # Ask the model to generate the strategy.
        result = model.invoke(
            [
                ("system", SYSTEM_PROMPT),
                ("human", human_prompt),
            ]
        )

        # Extract and validate the model response.
        raw_text = _extract_response_text(result.content)

        try:
            strategy = _parse_strategy_response(raw_text)

        except (ValueError, TypeError) as exc:
            previous_error = str(exc)

            if attempt == MAX_STRATEGY_ATTEMPTS - 1:
                raise ValueError(
                    "Failed to generate a valid StrategyOutput "
                    f"after {MAX_STRATEGY_ATTEMPTS} attempts. "
                    f"Last parsing error: {previous_error}"
                ) from exc

            continue

        # Reject duplicate topics and retry if attempts remain.
        try:
            validate_topic_is_new(
                strategy,
                recent_topics,
            )

        except ValueError as exc:
            duplicate_topic = strategy.topic
            previous_error = None

            if attempt == MAX_STRATEGY_ATTEMPTS - 1:
                raise ValueError(
                    "Failed to generate a new topic after "
                    f"{MAX_STRATEGY_ATTEMPTS} attempts. "
                    f"Last duplicate topic: {strategy.topic}"
                ) from exc

            continue

        # Topic is new, so return the validated strategy.
        return strategy

    # Defensive fallback.
    raise RuntimeError(
        "Strategy generation ended unexpectedly."
    )