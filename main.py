
from src.config import settings


def main():
    print("Multi-Agent Instagram Growth Brain")
    print(f"Environment: {settings.app_env}")
    print(f"Model: {settings.openai_model}")
    print(
        "API key configured:",
        bool(settings.openai_api_key)
        and settings.openai_api_key != "your_openai_api_key_here"
    )


if __name__ == "__main__":
    main()