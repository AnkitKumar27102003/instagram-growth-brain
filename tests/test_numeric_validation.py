
from types import SimpleNamespace

from src.agents.numeric_validation import validate_script_numbers


def make_script(text):
    return SimpleNamespace(
        segments=[SimpleNamespace(voiceover=text)]
    )


def make_research(claim, evidence="", status="supported"):
    return SimpleNamespace(
        key_facts=[
            SimpleNamespace(
                claim=claim,
                evidence=evidence,
                verification_status=status,
            )
        ]
    )


def test_matching_percentage_passes():
    result = validate_script_numbers(
        make_script("UPI accounts for 84% of digital payments."),
        make_research(
            "UPI accounts for 84% of digital payments."
        ),
    )
    assert result["passed"] is True
    assert result["unmatched_numbers"] == []


def test_mismatched_percentage_is_flagged():
    result = validate_script_numbers(
        make_script("UPI accounts for 85% of digital payments."),
        make_research(
            "UPI accounts for 84% of digital payments."
        ),
    )
    assert result["passed"] is False
    assert "85 percent" in result["unmatched_numbers"]


def test_number_supported_by_evidence_passes():
    result = validate_script_numbers(
        make_script("UPI processed 16.58 billion transactions."),
        make_research(
            "UPI had a major milestone.",
            "UPI processed 16.58 billion transactions.",
        ),
    )
    assert result["passed"] is True


def test_unverified_fact_does_not_support_script_number():
    result = validate_script_numbers(
        make_script("UPI accounts for 84% of digital payments."),
        make_research(
            "UPI accounts for 84% of digital payments.",
            status="needs_verification",
        ),
    )
    assert result["passed"] is False
    assert "84 percent" in result["unmatched_numbers"]


def test_script_without_numbers_passes():
    result = validate_script_numbers(
        make_script("UPI changed how people make payments."),
        make_research(
            "UPI supports instant digital payments."
        ),
    )
    assert result["passed"] is True