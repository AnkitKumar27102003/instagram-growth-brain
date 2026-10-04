
from src.analytics.verification_report import format_verification_report
from src.models.verification import (
    ClaimVerification,
    EvidenceAssessment,
    VerificationOutput,
)


def test_report_includes_claim_status_and_evidence():
    verification = VerificationOutput(
        topic="Oil prices and India",
        overall_status="supported",
        claim_verifications=[
            ClaimVerification(
                claim_id="C1",
                claim="India imports a large share of its crude oil.",
                status="supported",
                confidence=0.9,
                explanation="The retrieved evidence supports the claim.",
                evidence=[
                    EvidenceAssessment(
                        source_title="Example Energy Report",
                        source_url="https://example.com/report",
                        evidence_excerpt="India imports crude oil.",
                        supports_claim=True,
                        relevance_note="Directly relevant to the claim.",
                    )
                ],
            )
        ],
    )

    report = format_verification_report(verification)

    assert "Oil prices and India" in report
    assert "C1 | SUPPORTED" in report
    assert "India imports a large share" in report
    assert "https://example.com/report" in report
    assert "90%" in report


def test_report_handles_claim_without_evidence():
    verification = VerificationOutput(
        topic="Test topic",
        overall_status="needs_verification",
        claim_verifications=[
            ClaimVerification(
                claim_id="C1",
                claim="A claim needing further checking.",
                status="needs_verification",
                confidence=0.3,
                explanation="There is not enough evidence.",
                evidence=[],
            )
        ],
    )

    report = format_verification_report(verification)

    assert "NEEDS_VERIFICATION" in report
    assert "No usable evidence returned" in report