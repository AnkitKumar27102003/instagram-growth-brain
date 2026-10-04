
from typing import Literal
from urllib.parse import urlparse

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


VerificationStatus = Literal[
    "supported",
    "conflicting",
    "needs_verification",
]


class ResearchSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    url: str = Field(min_length=8)
    source_type: str = Field(min_length=1)

    @field_validator("title", "source_type")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        value = value.strip()

        parsed = urlparse(value)

        if (
            parsed.scheme not in ("http", "https")
            or not parsed.netloc
            or any(char.isspace() for char in value)
        ):
            raise ValueError(
                "Source URL must be a valid HTTP or HTTPS URL."
            )

        return value


class ResearchFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str = Field(min_length=5)
    evidence: str = Field(min_length=5)
    source_urls: list[str] = Field(min_length=1)

    # Explicit status is required; never assume a fact is supported.
    verification_status: VerificationStatus

    @field_validator("claim", "evidence")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value

    @field_validator("source_urls")
    @classmethod
    def validate_source_urls(cls, values: list[str]) -> list[str]:
        cleaned_urls = []

        for value in values:
            url = value.strip()
            parsed = urlparse(url)

            if (
                parsed.scheme not in ("http", "https")
                or not parsed.netloc
                or any(char.isspace() for char in url)
            ):
                raise ValueError(
                    f"Invalid source URL: {value}"
                )

            if url not in cleaned_urls:
                cleaned_urls.append(url)

        if not cleaned_urls:
            raise ValueError(
                "Every research fact must have at least one source URL."
            )

        return cleaned_urls


class ResearchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=3)
    summary: str = Field(min_length=10)
    key_facts: list[ResearchFact] = Field(min_length=1)
    context: list[str] = Field(default_factory=list)
    sources: list[ResearchSource] = Field(min_length=1)
    verification_notes: list[str] = Field(default_factory=list)

    @field_validator("topic", "summary")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value

    @field_validator("context", "verification_notes")
    @classmethod
    def clean_text_lists(cls, values: list[str]) -> list[str]:
        cleaned = []

        for value in values:
            text = value.strip()
            if text:
                cleaned.append(text)

        return cleaned

    @model_validator(mode="after")
    def validate_fact_sources(self):
        available_urls = {
            source.url for source in self.sources
        }

        for fact in self.key_facts:
            for url in fact.source_urls:
                if url not in available_urls:
                    raise ValueError(
                        "Fact references a URL missing from sources: "
                        f"{url}"
                    )

        return self
