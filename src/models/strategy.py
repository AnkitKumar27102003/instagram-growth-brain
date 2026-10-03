
from pydantic import BaseModel, ConfigDict, Field


class StrategyOutput(BaseModel):
    """Structured output produced by the Strategy Agent."""

    model_config = ConfigDict(extra="forbid")

    topic: str = Field(
        min_length=3,
        description="The proposed topic for the next post."
    )

    content_bucket: str = Field(
        min_length=2,
        description="The content category, such as Economy or History."
    )

    hook_style: str = Field(
        min_length=2,
        description="The opening hook style, such as Curiosity or Conflict."
    )

    format: str = Field(
        min_length=2,
        description="The proposed format, such as Documentary Reel."
    )

    tone: str = Field(
        min_length=2,
        description="The language and presentation style."
    )

    rationale: str = Field(
        min_length=10,
        description="Why this strategy was selected."
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the proposed strategy, from 0 to 1."
    )

    avoid_topics: list[str] = Field(
        default_factory=list,
        description="Topics the Writer Agent should avoid."
    )

    avoid_formats: list[str] = Field(
        default_factory=list,
        description="Formats the Writer Agent should avoid."
    )

    avoid_hook_styles: list[str] = Field(
        default_factory=list,
        description="Hook styles to avoid repeating."
    )