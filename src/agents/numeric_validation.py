
# src/agents/numeric_validation.py

import re
from typing import Any


# Match numbers with optional currency, percentage, or common units.
# This is deliberately conservative: it checks exact representations
# and does not infer equivalence between different units.
_NUMBER_PATTERN = re.compile(
    r"(?<![\w/])"
    r"(?P<currency>₹|rs\.?\s*)?"
    r"(?P<number>\d[\d,]*(?:\.\d+)?)"
    r"\s*"
    r"(?P<unit>"
    r"%|percent(?:age)?|"
    r"crores?|lakhs?|"
    r"millions?|billions?|trillions?|"
    r"thousands?|"
    r"rupees?|"
    r"km|kilomet(?:er|re)s?|"
    r"tonnes?|tons?|"
    r"kg|kgs|"
    r"l|litres?|liters?"
    r")?",
    re.IGNORECASE,
)

_UNIT_ALIASES = {
    "%": "percent",
    "percent": "percent",
    "percentage": "percent",
    "crore": "crore",
    "crores": "crore",
    "lakh": "lakh",
    "lakhs": "lakh",
    "million": "million",
    "millions": "million",
    "billion": "billion",
    "billions": "billion",
    "trillion": "trillion",
    "trillions": "trillion",
    "thousand": "thousand",
    "thousands": "thousand",
    "rupee": "rupee",
    "rupees": "rupee",
    "km": "km",
    "kilometer": "km",
    "kilometers": "km",
    "kilometre": "km",
    "kilometres": "km",
    "tonne": "tonne",
    "tonnes": "tonne",
    "ton": "tonne",
    "tons": "tonne",
    "kg": "kg",
    "kgs": "kg",
    "l": "litre",
    "litre": "litre",
    "litres": "litre",
    "liter": "litre",
    "liters": "litre",
}


def _normalize_number(value: str) -> str:
    """Normalize formatting while preserving numeric value."""
    number = float(value.replace(",", ""))
    if number.is_integer():
        return str(int(number))
    return format(number, ".12g")


def _extract_numeric_tokens(text: str) -> set[str]:
    """Return normalized numeric tokens from text."""
    tokens = set()

    for match in _NUMBER_PATTERN.finditer(text or ""):
        number = _normalize_number(match.group("number"))
        unit = (match.group("unit") or "").lower()
        currency = (match.group("currency") or "").strip().lower()

        normalized_unit = _UNIT_ALIASES.get(unit, unit)

        if currency:
            normalized_unit = "rupee"

        token = f"{number} {normalized_unit}".strip()
        tokens.add(token)

    return tokens


def validate_script_numbers(
    script: Any,
    research: Any,
) -> dict:
    """
    Compare numeric tokens in script voiceover with supported
    research claims and evidence.

    This is a conservative consistency check, not a fact-checker.
    Any unmatched number should be reviewed by a human.
    """
    script_text = " ".join(
        segment.voiceover for segment in script.segments
    )

    supported_text_parts = []

    for fact in research.key_facts:
        if fact.verification_status != "supported":
            continue

        supported_text_parts.extend([
            fact.claim,
            fact.evidence,
        ])

    supported_text = " ".join(supported_text_parts)

    script_tokens = _extract_numeric_tokens(script_text)
    supported_tokens = _extract_numeric_tokens(supported_text)

    unmatched = sorted(script_tokens - supported_tokens)

    issues = [
        {
            "token": token,
            "message": (
                f"Script contains '{token}', which was not found "
                "in supported research claims or evidence. "
                "Review the original source before approval."
            ),
        }
        for token in unmatched
    ]

    return {
        "passed": len(issues) == 0,
        "script_numbers": sorted(script_tokens),
        "supported_research_numbers": sorted(supported_tokens),
        "unmatched_numbers": unmatched,
        "issues": issues,
    }