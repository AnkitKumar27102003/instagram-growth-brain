
from pydantic import BaseModel, ConfigDict, Field


class CritiqueScores(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hook_strength: float = Field(ge=1, le=10)
    emotional_arc: float = Field(ge=1, le=10)
    pacing: float = Field(ge=1, le=10)
    originality: float = Field(ge=1, le=10)
    nazar_alignment: float = Field(ge=1, le=10)


class CritiqueOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scores: CritiqueScores
    strengths: list[str] = Field(min_length=1)
    weaknesses: list[str] = Field(min_length=1)
    revision_instructions: list[str] = Field(default_factory=list)
