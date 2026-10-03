
from src.agents.strategy_agent import generate_strategy
from src.agents.writer_agent import generate_script


def main():
    account_id = "nazar.for.world"

    print("Generating NAZAR content strategy...")
    strategy = generate_strategy(account_id)

    print("\nSTRATEGY")
    print("=" * 40)
    print(strategy.model_dump_json(indent=4))

    print("\nGenerating Reel script...")
    script = generate_script(strategy)

    print("\nWRITER AGENT OUTPUT")
    print("=" * 40)
    print(script.model_dump_json(indent=4))

    print("\nWORD COUNT CHECK")
    print("=" * 40)

    for segment in script.segments:
        word_count = len(segment.voiceover.split())
        print(f"Segment {segment.segment_number}: {word_count} words")


if __name__ == "__main__":
    main()
