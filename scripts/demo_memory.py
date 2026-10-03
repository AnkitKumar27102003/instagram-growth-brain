
import json

from src.memory.database import get_connection
from src.memory.performance_memory import (
    save_approved_script,
    record_performance_feedback,
    get_recent_content,
    get_performance_patterns,
)

ACCOUNT_ID = "nazar.for.world"


def main():
    print("NAZAR — PERFORMANCE MEMORY DEMO")
    print("=" * 40)

    # Step 1: Verify the account exists
    connection = get_connection()
    try:
        account = connection.execute(
            "SELECT account_id, name FROM accounts WHERE account_id = ?",
            (ACCOUNT_ID,),
        ).fetchone()
    finally:
        connection.close()

    print("Account ID being used:", repr(ACCOUNT_ID))
    print("Account exists:", account is not None)

    if account is None:
        print(
            "\nERROR: Account not found in the connected database."
            "\nCheck the account ID and database path."
        )
        return

    print(f"Account name: {account['name']}")

    # Step 2: Save an approved demo script
    try:
        script_id = save_approved_script(
            account_id=ACCOUNT_ID,
            topic="Why do oil prices affect India?",
            content_bucket="Economy",
            hook_style="Curiosity",
            format="Documentary Reel",
            tone="Informative Hinglish",
            strategy={
                "reason": "Demo strategy for testing performance memory",
                "confidence": 0.8,
                "source": "synthetic_demo",
            },
            script_text=(
                "Socho, agar duniya mein oil mehenga ho jaaye, "
                "toh India ki economy par kya asar padega?"
            ),
            critic_score=9.0,
        )

        print(f"\nApproved script saved: {script_id}")

        # Step 3: Record simulated performance
        metrics = {
            "views": 50000,
            "reach": 40000,
            "likes": 3200,
            "shares": 800,
            "saves": 600,
            "comments": 200,
            "watch_time_avg_seconds": 25.0,
            "followers_gained": 180,
        }

        feedback_id = record_performance_feedback(
            script_id=script_id,
            metrics=metrics,
            is_simulated=True,
        )

        print(f"Simulated feedback saved: {feedback_id}")

        # Step 4: Display calculated metrics
        interactions = (
            metrics["likes"]
            + metrics["comments"]
            + metrics["shares"]
            + metrics["saves"]
        )

        calculated_metrics = {
            "engagement_rate": round(
                interactions / metrics["reach"] * 100, 2
            ),
            "share_rate": round(
                metrics["shares"] / metrics["reach"] * 100, 2
            ),
            "save_rate": round(
                metrics["saves"] / metrics["reach"] * 100, 2
            ),
            "follower_conversion_rate": round(
                metrics["followers_gained"]
                / metrics["reach"] * 100,
                2,
            ),
        }

        print("\nSIMULATED PERFORMANCE METRICS")
        print(json.dumps(calculated_metrics, indent=4))

        # Step 5: Retrieve recent approved scripts
        recent = get_recent_content(
            account_id=ACCOUNT_ID,
            limit=5,
        )

        print("\nRECENT APPROVED SCRIPTS")
        print(json.dumps(recent, indent=4, ensure_ascii=False))

        # Step 6: Retrieve historical performance patterns
        patterns = get_performance_patterns(
            account_id=ACCOUNT_ID,
        )

        print("\nPERFORMANCE PATTERNS")
        print(json.dumps(patterns, indent=4, ensure_ascii=False))

        print("\nDemo completed successfully.")

    except Exception as error:
        print(f"\nERROR: {type(error).__name__}: {error}")
        raise


if __name__ == "__main__":
    main()