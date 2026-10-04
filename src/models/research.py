
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class ResearchSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    url: str = Field(min_length=8)
    source_type: str = Field(min_length=1)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith(("https://", "http://")):
            raise ValueError("Source URL must start with http:// or https://")
        return value


class ResearchFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str = Field(min_length=5)
    evidence: str = Field(min_length=5)
    source_urls: list[str] = Field(min_length=1)
    verification_status: Literal[
        "supported",
        "conflicting",
        "needs_verification",
    ] = "supported"


class ResearchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=3)
    summary: str = Field(min_length=10)
    key_facts: list[ResearchFact] = Field(min_length=1)
    context: list[str] = Field(default_factory=list)
    sources: list[ResearchSource] = Field(min_length=1)
    verification_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_fact_sources(self):
        available_urls = {source.url for source in self.sources}

        for fact in self.key_facts:
            for url in fact.source_urls:
                if url not in available_urls:
                    raise ValueError(
                        f"Fact references a URL missing from sources: {url}"
                    )

        return self