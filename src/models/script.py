
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScriptSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segment_number: int = Field(ge=1)
    voiceover: str = Field(min_length=1)
    visual_direction: str = Field(min_length=1)

    @field_validator("voiceover")
    @classmethod
    def validate_word_count(cls, value: str) -> str:
        word_count = len(value.split())

        if not 18 <= word_count <= 23:
            raise ValueError(
                f"Voiceover must contain 18–23 words; got {word_count}"
            )

        return value


class ScriptOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=3)
    content_bucket: str = Field(min_length=2)
    hook_style: str = Field(min_length=2)
    segments: list[ScriptSegment] = Field(min_length=1)
    call_to_action: str = Field(min_length=1)
