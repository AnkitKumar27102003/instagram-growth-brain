
from typing import Literal

from pydantic import BaseModel, Field, model_validator


VerificationStatus = Literal[
    "supported",
    "conflicting",
    "needs_verification",
]


class EvidenceAssessment(BaseModel):
    source_title: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    evidence_excerpt: str = Field(min_length=1)
    supports_claim: bool
    relevance_note: str = Field(min_length=1)


class ClaimVerification(BaseModel):
    claim_id: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    status: VerificationStatus
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str = Field(min_length=1)
    evidence: list[EvidenceAssessment] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_evidence(self):
        if self.status == "supported":
            if not any(item.supports_claim for item in self.evidence):
                raise ValueError(
                    "Supported claims must have supporting evidence."
                )

        if self.status == "conflicting":
            if not (
                any(item.supports_claim for item in self.evidence)
                and any(not item.supports_claim for item in self.evidence)
            ):
                raise ValueError(
                    "Conflicting claims need both supporting "
                    "and contradicting evidence."
                )

        return self


class VerificationOutput(BaseModel):
    topic: str = Field(min_length=1)
    claim_verifications: list[ClaimVerification] = Field(min_length=1)
    overall_status: VerificationStatus

    @model_validator(mode="after")
    def validate_overall_status(self):
        statuses = {item.status for item in self.claim_verifications}

        if "conflicting" in statuses:
            expected = "conflicting"
        elif "needs_verification" in statuses:
            expected = "needs_verification"
        else:
            expected = "supported"

        if self.overall_status != expected:
            raise ValueError(
                f"Overall status should be '{expected}'."
            )

        return self