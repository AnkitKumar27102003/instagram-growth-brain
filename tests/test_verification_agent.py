
import pytest

from src.agents.verification_agent import _validate_verification
from src.models.research import (
    ResearchFact,
    ResearchOutput,
    ResearchSource,
)
from src.models.verification import (
    ClaimVerification,
    EvidenceAssessment,
    VerificationOutput,
)


def sample_research():
    return ResearchOutput(
        topic="GST in India",
        summary="A short research summary about GST.",
        key_facts=[
            ResearchFact(
                claim="GST is a consumption-based tax in India.",
                evidence=(
                    "The supplied research describes GST "
                    "as a consumption tax."
                ),
                source_urls=[
                    "https://example.com/research"
                ],
                verification_status="supported",
            )
        ],
        sources=[
            ResearchSource(
                title="Research Source",
                url="https://example.com/research",
                source_type="article",
            )
        ],
    )



def sample_output(url="https://example.com/verification"):
    return VerificationOutput(
        topic="GST in India",
        claim_verifications=[
            ClaimVerification(
                claim_id="C1",
                claim="GST is a consumption-based tax in India.",
                status="supported",
                confidence=0.85,
                explanation="The search result supports the claim.",
                evidence=[
                    EvidenceAssessment(
                        source_title="GST Report",
                        source_url=url,
                        evidence_excerpt=(
                            "GST is a consumption-based tax in India."
                        ),
                        supports_claim=True,
                        relevance_note="Directly relevant to the claim.",
                    )
                ],
            )
        ],
        overall_status="supported",
    )


def sample_search_results():
    return [
        {
            "claim_id": "C1",
            "title": "GST Report",
            "url": "https://example.com/verification",
            "content": (
                "GST is a consumption-based tax in India."
            ),
        }
    ]


def test_valid_verification_passes():
    _validate_verification(
        sample_output(),
        sample_research(),
        sample_search_results(),
    )


def test_unretrieved_evidence_url_fails():
    with pytest.raises(ValueError, match="not returned"):
        _validate_verification(
            sample_output("https://fake.example/report"),
            sample_research(),
            sample_search_results(),
        )


def test_invented_excerpt_fails():
    output = sample_output()
    output.claim_verifications[0].evidence[0].evidence_excerpt = (
        "This text is not in the search result."
    )

    with pytest.raises(ValueError, match="not present"):
        _validate_verification(
            output,
            sample_research(),
            sample_search_results(),
        )


def test_mismatched_claim_fails():
    output = sample_output()
    output.claim_verifications[0].claim = (
        "A different claim about GST."
    )

    with pytest.raises(ValueError, match="does not match"):
        _validate_verification(
            output,
            sample_research(),
            sample_search_results(),
        )