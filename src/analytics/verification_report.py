
from src.models.verification import VerificationOutput


def format_verification_report(
    verification: VerificationOutput,
) -> str:
    """Format claim-level verification results for human review."""

    lines = [
        "=" * 64,
        "NAZAR — FACTUAL VERIFICATION REPORT",
        "=" * 64,
        f"Topic: {verification.topic}",
        f"Overall status: {verification.overall_status.upper()}",
        f"Claims reviewed: {len(verification.claim_verifications)}",
        "",
    ]

    for item in verification.claim_verifications:
        lines.extend([
            "-" * 64,
            f"{item.claim_id} | {item.status.upper()}",
            f"Claim: {item.claim}",
            f"Confidence: {item.confidence:.0%}",
            f"Assessment: {item.explanation}",
        ])

        if item.evidence:
            lines.append("Evidence:")

            for index, evidence in enumerate(item.evidence, start=1):
                position = (
                    "Supports" if evidence.supports_claim
                    else "Contradicts / does not support"
                )
                lines.extend([
                    f"  {index}. {position}",
                    f"     Source: {evidence.source_title}",
                    f"     URL: {evidence.source_url}",
                    f"     Excerpt: {evidence.evidence_excerpt}",
                    f"     Relevance: {evidence.relevance_note}",
                ])
        else:
            lines.append("Evidence: No usable evidence returned.")

        lines.append("")

    lines.extend([
        "=" * 64,
        "REVIEW NOTE",
        "Search-result evidence is not a substitute for checking",
        "the original source. Review claims marked conflicting or",
        "needs_verification before publishing.",
        "=" * 64,
    ])

    return "\n".join(lines)