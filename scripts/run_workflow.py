
import json

from src.graph.content_workflow import run_content_workflow


def main():
    account_id = "nazar.for.world"

    print("\nNAZAR — MULTI-AGENT CONTENT WORKFLOW")
    print("=" * 50)
    print("Running Strategy, Writer, and Critic Agents...\n")

    result = run_content_workflow(account_id)

    print("\nCONTENT STRATEGY")
    print("-" * 50)
    print(json.dumps(
        result["strategy"].model_dump(),
        indent=4,
        ensure_ascii=False
    ))

    print("\nFINAL SCRIPT")
    print("-" * 50)

    script = result["script"]

    print(f"Topic: {script.topic}")
    print(f"Content bucket: {script.content_bucket}")
    print(f"Hook style: {script.hook_style}\n")

    for segment in script.segments:
        word_count = len(segment.voiceover.split())

        print(f"Segment {segment.segment_number} ({word_count} words)")
        print(f"Voiceover: {segment.voiceover}")
        print(f"Visual: {segment.visual_direction}\n")

    print(f"CTA: {script.call_to_action}")

    print("\nFINAL CRITIQUE")
    print("-" * 50)
    print(json.dumps(
        result["critique"].model_dump(),
        indent=4,
        ensure_ascii=False
    ))

    print("\nWORKFLOW SUMMARY")
    print("-" * 50)
    print(f"Overall score: {result['overall_score']}/10")
    print(f"Passed: {result['passed']}")
    print(f"Revision rounds: {result['revision_rounds']}")

    print("\nREVISION HISTORY")
    print("-" * 50)
    print(json.dumps(
        result["revision_history"],
        indent=4,
        ensure_ascii=False
    ))


if __name__ == "__main__":
    main()