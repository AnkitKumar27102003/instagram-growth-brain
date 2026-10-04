
import json
import sys

from src.graph.content_workflow import run_content_workflow
from src.analytics.verification_report import format_verification_report


ACCOUNT_ID = "nazar.for.world"


def make_json_serializable(value):
    """Convert Pydantic models and nested objects into JSON-compatible data."""
    if hasattr(value, "model_dump"):
        return make_json_serializable(value.model_dump())

    if isinstance(value, dict):
        return {
            key: make_json_serializable(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [make_json_serializable(item) for item in value]

    if hasattr(value, "value"):
        return make_json_serializable(value.value)

    return value


def main():
    print("\nNAZAR — CONTENT GENERATION WORKFLOW")
    print("=" * 45)
    print(f"Account: {ACCOUNT_ID}")
    print(
        "\nRunning Strategy → Research → Verification "
        "→ Script → Critic...\n"
    )

    try:
        result = run_content_workflow(account_id=ACCOUNT_ID)
    except Exception as exc:
        print(f"\nWorkflow failed: {exc}", file=sys.stderr)
        raise

    # Generate the report before converting Pydantic models to dictionaries.
    verification = result.get("verification")

    print("\nNAZAR — FACTUAL VERIFICATION REPORT")
    print("=" * 45)

    if verification is not None:
        print(format_verification_report(verification))
    else:
        print("No verification results were returned.")

    # Convert the complete workflow result for JSON output.
    result = make_json_serializable(result)

    print("\nNAZAR — WORKFLOW REPORT")
    print("=" * 45)

    print("\nSTRATEGY")
    print("-" * 45)
    print(json.dumps(result.get("strategy"), indent=4, ensure_ascii=False))

    print("\nRESEARCH")
    print("-" * 45)
    print(json.dumps(result.get("research"), indent=4, ensure_ascii=False))

    print("\nVERIFIED RESEARCH")
    print("-" * 45)
    print(
        json.dumps(
            result.get("verified_research"),
            indent=4,
            ensure_ascii=False,
        )
    )

    print("\nVERIFICATION DATA")
    print("-" * 45)
    print(
        json.dumps(
            result.get("verification"),
            indent=4,
            ensure_ascii=False,
        )
    )

    print("\nFINAL SCRIPT")
    print("-" * 45)
    print(json.dumps(result.get("script"), indent=4, ensure_ascii=False))

    print("\nCRITIC")
    print("-" * 45)
    print(json.dumps(result.get("critique"), indent=4, ensure_ascii=False))

    print("\nWORKFLOW SUMMARY")
    print("-" * 45)
    summary = {
        "overall_score": result.get("overall_score"),
        "revision_rounds": result.get("revision_rounds"),
        "passed": result.get("passed"),
        "facts_supported": result.get("facts_supported"),
        "saved_script_id": result.get("saved_script_id"),
        "verification_status": (
            result.get("verification", {}).get("overall_status")
            if isinstance(result.get("verification"), dict)
            else None
        ),
    }
    print(json.dumps(summary, indent=4, ensure_ascii=False))

    print("\nREVISION HISTORY")
    print("-" * 45)
    print(
        json.dumps(
            result.get("revision_history", []),
            indent=4,
            ensure_ascii=False,
        )
    )

    if result.get("passed"):
        print(
            "\nWorkflow completed: script passed the critic "
            "and factual verification approval gate."
        )
    else:
        print(
            "\nWorkflow completed: script did not meet "
            "all approval requirements."
        )

    print("=" * 45)


if __name__ == "__main__":
    main()