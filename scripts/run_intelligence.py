
import json

from src.analytics.intelligence import generate_intelligence_report


def main():
    report = generate_intelligence_report()

    print("\nNAZAR — CHANNEL INTELLIGENCE REPORT")
    print("=" * 45)

    print(json.dumps(report, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()