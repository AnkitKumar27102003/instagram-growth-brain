
from src.agents.strategy_agent import generate_strategy


def main():
    account_id = "nazar.for.world"

    print("Generating NAZAR content strategy...")
    strategy = generate_strategy(account_id)

    print("\nSTRATEGY AGENT OUTPUT")
    print("=" * 40)
    print(strategy.model_dump_json(indent=4))


if __name__ == "__main__":
    main()