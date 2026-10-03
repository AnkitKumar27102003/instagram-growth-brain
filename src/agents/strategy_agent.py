
import json
from functools import lru_cache

from sentence_transformers import SentenceTransformer
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
        raise ValueError("Similarity threshold must be between 0 and 1.")

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


def _parse_strategy_response(raw_text: str) -> StrategyOutput:
    """Parse JSON and validate it using the Pydantic model."""
    raw_text = raw_text.strip()

    # Remove Markdown fences if the model adds them.
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        raw_text = "\n".join(lines).strip()

        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:].strip()

    try:
        parsed_data = json.loads(raw_text)
        return StrategyOutput.model_validate(parsed_data)

    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise ValueError(
            "The model did not return valid StrategyOutput JSON. "
            "Try again or select another OpenRouter model. "
            f"Parsing details: {exc}"
        ) from exc


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
    )

    duplicate_topic = None

    for attempt in range(MAX_STRATEGY_ATTEMPTS):
        # Build the prompt for this attempt.
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

        # Add feedback if a previous attempt generated a duplicate.
        if duplicate_topic is not None:
            human_prompt = (
                "Your previous response repeated a recently "
                "covered topic.\n\n"
                f"Rejected topic: {duplicate_topic}\n\n"
                "Generate a genuinely different topic. "
                "Do not use the same topic with different wording "
                "or cover the same underlying subject again. "
                "Choose a distinct subject while following "
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

        # Extract and validate the model response.
        raw_text = _extract_response_text(result.content)
        strategy = _parse_strategy_response(raw_text)

        # Reject duplicate topics and retry if attempts remain.
        try:
            validate_topic_is_new(
                strategy,
                recent_topics,
            )

        except ValueError as exc:
            duplicate_topic = strategy.topic

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