
from src.config import settings


def is_configured(value: str) -> bool:
    """Check whether an API key is present and not a placeholder."""
    if not value:
        return False

    normalized = value.strip().lower()

    return normalized not in {
        "",
        "your_openai_api_key_here",
        "your_openrouter_api_key_here",
        "your_tavily_api_key_here",
    }


def main():
    print("=" * 50)
    print("NAZAR - Instagram Growth Brain")
    print("=" * 50)

    print(f"Environment: {settings.app_env}")

    openrouter_ready = is_configured(
        settings.openrouter_api_key
    )
    tavily_ready = is_configured(
        settings.tavily_api_key
    )
    openai_ready = is_configured(
        settings.openai_api_key
    )

    print("\nAPI Configuration")
    print("-" * 50)

    print(
        f"OpenRouter: {'Configured' if openrouter_ready else 'Missing'}"
    )
    if openrouter_ready:
        print(f"OpenRouter model: {settings.openrouter_model}")

    print(
        f"Tavily: {'Configured' if tavily_ready else 'Missing'}"
    )

    print(
        f"OpenAI: {'Configured' if openai_ready else 'Missing'}"
    )
    if openai_ready:
        print(f"OpenAI model: {settings.openai_model}")

    print("\nWorkflow Readiness")
    print("-" * 50)

    if openrouter_ready and tavily_ready:
        print("Core API configuration: Ready")
    else:
        print("Core API configuration: Incomplete")
        if not openrouter_ready:
            print("- Add a valid OPENROUTER_API_KEY to .env")
        if not tavily_ready:
            print("- Add a valid TAVILY_API_KEY to .env")

    print("=" * 50)


if __name__ == "__main__":
    main()
