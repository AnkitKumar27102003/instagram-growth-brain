
import argparse
import json

from src.memory.database import get_connection
from src.memory.performance_memory import (
    save_approved_script,
    record_performance_feedback,
    get_recent_content,
    get_performance_patterns,
)
from src.analytics.fatigue import detect_feedback_topic_fatigue
from src.analytics.performance import detect_breakout_content


ACCOUNT_ID = "nazar.for.world"

# These are synthetic examples for testing the memory pipeline.
# They are not real Instagram performance results.
DEMO_RECORDS = [
    {
        "script_id": "nazar-demo-oil-01",
        "feedback_id": "nazar-demo-feedback-oil-01",
        "topic": "Why oil prices affect India",
        "script_text": (
            "Socho, agar duniya mein oil mehenga ho jaaye, "
            "toh India ki economy par kya asar padega?"
        ),
        "metrics": {
            "views": 50000,
            "reach": 40000,
            "likes": 3200,
            "shares": 800,
            "saves": 600,
            "comments": 200,
            "watch_time_avg_seconds": 25.0,
            "followers_gained": 180,
        },
    },
    {
        "script_id": "nazar-demo-upi-01",
        "feedback_id": "nazar-demo-feedback-upi-01",
        "topic": "How India's UPI system works",
        "script_text": (
            "Aaj hum phone se seconds mein payment karte hain, "
            "lekin UPI ke peeche ka system kaise kaam karta hai?"
        ),
        "metrics": {
            "views": 45000,
            "reach": 40000,
            "likes": 2600,
            "shares": 500,
            "saves": 450,
            "comments": 150,
            "watch_time_avg_seconds": 21.0,
            "followers_gained": 120,
        },
    },
    {
        "script_id": "nazar-demo-inflation-01",
        "feedback_id": "nazar-demo-feedback-inflation-01",
        "topic": "Why everyday items become expensive",
        "script_text": (
            "Kabhi socha hai ki wahi samaan jo kal sasta tha, "
            "aaj mehenga kyun mil raha hai?"
        ),
        "metrics": {
            "views": 48000,
            "reach": 40000,
            "likes": 3000,
            "shares": 600,
            "saves": 500,
            "comments": 200,
            "watch_time_avg_seconds": 23.0,
            "followers_gained": 145,
        },
    },
    {
        "script_id": "nazar-demo-budget-01",
        "feedback_id": "nazar-demo-feedback-budget-01",
        "topic": "Where does India's tax money go",
        "script_text": (
            "Aap tax dete hain, lekin kya aap jaante hain "
            "ki sarkar is paise ko kahan kharch karti hai?"
        ),
        "metrics": {
            "views": 90000,
            "reach": 40000,
            "likes": 9000,
            "shares": 2500,
            "saves": 2000,
            "comments": 500,
            "watch_time_avg_seconds": 34.0,
            "followers_gained": 520,
        },
    },
]


def print_json(title, data):
    print(f"\n{title}")
    print("-" * len(title))
    print(json.dumps(data, indent=4, ensure_ascii=False, default=str))


def account_exists():
    connection = get_connection()
    try:
        return connection.execute(
            """
            SELECT account_id, name
            FROM accounts
            WHERE account_id = ?
            """,
            (ACCOUNT_ID,),
        ).fetchone()
    finally:
        connection.close()


def script_exists(script_id):
    connection = get_connection()
    try:
        return connection.execute(
            """
            SELECT 1
            FROM approved_scripts
            WHERE script_id = ?
            """,
            (script_id,),
        ).fetchone() is not None
    finally:
        connection.close()


def feedback_exists(feedback_id):
    connection = get_connection()
    try:
        return connection.execute(
            """
            SELECT 1
            FROM performance_feedback
            WHERE feedback_id = ?
            """,
            (feedback_id,),
        ).fetchone() is not None
    finally:
        connection.close()


def save_demo_records():
    """Insert the synthetic records only if they do not exist."""
    scripts_added = 0
    feedback_added = 0

    for record in DEMO_RECORDS:
        script_id = record["script_id"]

        if not script_exists(script_id):
            save_approved_script(
                account_id=ACCOUNT_ID,
                topic=record["topic"],
                content_bucket="Economy",
                hook_style="Curiosity",
                format="Documentary Reel",
                tone="Informative Hinglish",
                strategy={
                    "reason": "Synthetic demo record for testing memory",
                    "confidence": 0.8,
                    "source": "synthetic_demo",
                },
                script_text=record["script_text"],
                critic_score=9.0,
                script_id=script_id,
            )
            scripts_added += 1

        feedback_id = record["feedback_id"]

        if not feedback_exists(feedback_id):
            record_performance_feedback(
                script_id=script_id,
                metrics=record["metrics"],
                is_simulated=True,
                feedback_id=feedback_id,
            )
            feedback_added += 1

    return scripts_added, feedback_added


def calculate_metrics(metrics):
    reach = metrics["reach"]
    interactions = (
        metrics["likes"]
        + metrics["comments"]
        + metrics["shares"]
        + metrics["saves"]
    )

    return {
        "engagement_rate_percent": round(
            interactions / reach * 100, 2
        ),
        "share_rate_percent": round(
            metrics["shares"] / reach * 100, 2
        ),
        "save_rate_percent": round(
            metrics["saves"] / reach * 100, 2
        ),
        "follower_conversion_rate_percent": round(
            metrics["followers_gained"] / reach * 100, 2
        ),
    }


def main(generate_next_strategy=False):
    print("NAZAR — PERFORMANCE MEMORY & LEARNING DEMO")
    print("=" * 48)
    print("All example performance figures are SIMULATED.")

    account = account_exists()

    print(f"\nAccount ID: {ACCOUNT_ID}")
    print(f"Account exists: {account is not None}")

    if account is None:
        print(
            "\nERROR: Account not found in the connected database."
            "\nCheck the account ID and database configuration."
        )
        return

    print(f"Account name: {account['name']}")

    # Step 1: Save synthetic demo data idempotently.
    scripts_added, feedback_added = save_demo_records()

    print("\nDEMO DATA")
    print("---------")
    print(f"New approved scripts inserted: {scripts_added}")
    print(f"New simulated feedback records inserted: {feedback_added}")
    print("Existing demo records were left unchanged.")

    # Step 2: Show the metrics for each synthetic record.
    print("\nSIMULATED SCRIPT METRICS")
    print("------------------------")

    for record in DEMO_RECORDS:
        print(f"\nTopic: {record['topic']}")
        print_json(
            "Calculated metrics",
            calculate_metrics(record["metrics"]),
        )

    # Step 3: Retrieve recent approved content.
    recent = get_recent_content(
        account_id=ACCOUNT_ID,
        limit=10,
    )
    print_json("RECENT APPROVED SCRIPTS", recent)

    # Step 4: Retrieve historical performance patterns.
    patterns = get_performance_patterns(
        account_id=ACCOUNT_ID,
    )
    print_json("PERFORMANCE PATTERNS", patterns)

    # Step 5: Evaluate possible topic fatigue.
    fatigue = detect_feedback_topic_fatigue(
        account_id=ACCOUNT_ID,
    )
    print_json("TOPIC FATIGUE SIGNALS", fatigue)

    # Step 6: Detect breakout candidates.
    breakout = detect_breakout_content(
        account_id=ACCOUNT_ID,
    )
    print_json("BREAKOUT CONTENT SIGNALS", breakout)

    # Step 7: Optionally generate a new strategy using memory.
    if generate_next_strategy:
        print("\nGENERATING NEXT STRATEGY")
        print("------------------------")

        from src.agents.strategy_agent import generate_strategy

        strategy = generate_strategy(
            account_id=ACCOUNT_ID,
            content_goal=(
                "Recommend a fresh NAZAR Reel idea using "
                "historical performance, topic fatigue, "
                "and breakout patterns."
            ),
        )

        print_json(
            "NEXT STRATEGY",
            strategy.model_dump(),
        )
    else:
        print(
            "\nStrategy generation skipped. "
            "Use --generate-strategy to invoke the LLM."
        )

    print("\nDemo completed successfully.")
    print(
        "Reminder: synthetic feedback is for testing only "
        "and must not be presented as real Instagram performance."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the NAZAR performance memory demo."
    )
    parser.add_argument(
        "--generate-strategy",
        action="store_true",
        help=(
            "Generate a new strategy using the memory signals. "
            "Requires a valid model API key."
        ),
    )
    args = parser.parse_args()

    try:
        main(generate_next_strategy=args.generate_strategy)
    except Exception as error:
        print(f"\nERROR: {type(error).__name__}: {error}")
        raise
