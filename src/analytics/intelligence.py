
from src.analytics.performance import analyze_account
from src.analytics.content_gaps import detect_content_gaps
from src.analytics.fatigue import detect_topic_fatigue


def generate_intelligence_report() -> dict:
    """Combine account analysis into one report."""

    performance = analyze_account()
    gaps = detect_content_gaps()
    fatigue = detect_topic_fatigue()

    return {
        "account_performance": {
            "post_count": performance["post_count"],
            "average_metrics": performance["average_metrics"],
            "topic_performance": performance["topic_performance"],
        },
        "content_gaps": gaps,
        "topic_fatigue": fatigue,
    }