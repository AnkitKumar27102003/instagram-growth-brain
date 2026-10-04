
import pytest
from pydantic import ValidationError

from src.models.verification import (
    ClaimVerification,
    EvidenceAssessment,
    VerificationOutput,
)


def make_evidence(supports=True):
    return EvidenceAssessment(
        source_title="Official source",
        source_url="https://example.com/report",
        evidence_excerpt="The report provides relevant evidence.",
        supports_claim=supports,
        relevance_note="Relevant to the claim.",
    )


def test_supported_claim_requires_evidence():
    claim = ClaimVerification(
        claim_id="C1",
        claim="Example factual claim",
        status="supported",
        confidence=0.9,
        explanation="Evidence supports the claim.",
        evidence=[make_evidence(True)],
    )
    assert claim.status == "supported"


def test_supported_claim_without_support_fails():
    with pytest.raises(ValidationError):
        ClaimVerification(
            claim_id="C1",
            claim="Example factual claim",
            status="supported",
            confidence=0.9,
            explanation="No supporting evidence.",
            evidence=[],
        )


def test_conflicting_claim_requires_both_sides():
    with pytest.raises(ValidationError):
        ClaimVerification(
            claim_id="C1",
            claim="Example factual claim",
            status="conflicting",
            confidence=0.5,
            explanation="Evidence is inconsistent.",
            evidence=[make_evidence(True)],
        )


def test_overall_status_reflects_claim_statuses():
    output = VerificationOutput(
        topic="GST",
        claim_verifications=[
            ClaimVerification(
                claim_id="C1",
                claim="Example factual claim",
                status="needs_verification",
                confidence=0.4,
                explanation="More evidence is needed.",
            )
        ],
        overall_status="needs_verification",
    )
    assert output.overall_status == "needs_verification"