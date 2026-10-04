
from src.memory.database import get_connection
from src.analytics.performance import calculate_post_metrics


def detect_topic_fatigue(recent_limit: int = 5) -> dict:
    """Flag repeated topics and possible performance decline."""

    if recent_limit < 1:
        raise ValueError("recent_limit must be positive.")

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM posts
            ORDER BY published_at DESC, post_id DESC
            LIMIT ?
            """,
            (recent_limit,),
        ).fetchall()

    recent_posts = [
        calculate_post_metrics(row) for row in rows
    ]

    topic_groups = {}

    for post in recent_posts:
        topic_groups.setdefault(post["topic"], []).append(post)

    fatigue_candidates = []

    for topic, group in topic_groups.items():
        if len(group) < 2:
            continue

        # Posts are ordered newest to oldest.
        latest = group[0]
        previous = group[1]

        previous_rate = previous["engagement_rate"]
        latest_rate = latest["engagement_rate"]

        if previous_rate > 0:
            decline_percent = round(
                (previous_rate - latest_rate)
                / previous_rate * 100,
                2,
            )
        else:
            decline_percent = 0

        repeated = len(group) >= 2
        declining = decline_percent >= 30

        fatigue_candidates.append({
            "topic": topic,
            "recent_post_count": len(group),
            "latest_engagement_rate": latest_rate,
            "previous_engagement_rate": previous_rate,
            "engagement_decline_percent": decline_percent,
            "repeated_recently": repeated,
            "possible_performance_decline": declining,
            "fatigue_candidate": repeated and declining,
        })

    return {
        "recent_posts_checked": len(recent_posts),
        "fatigue_candidates": fatigue_candidates,
        "note": (
            "These are screening signals, not causal proof "
            "of audience fatigue. More posts and context "
            "are needed for a reliable conclusion."
        ),
    }


def detect_feedback_topic_fatigue(
    account_id: str,
    recent_limit: int = 20,
    decline_threshold: float = 30.0,
) -> dict:
    """Detect possible topic fatigue from approved-script feedback.

    Simulated and real feedback are analysed separately.
    A decline is a screening signal, not proof of audience fatigue.
    """
    if not account_id or not account_id.strip():
        raise ValueError("account_id must not be empty.")
    if recent_limit < 1:
        raise ValueError("recent_limit must be positive.")
    if not 0 <= decline_threshold <= 100:
        raise ValueError("decline_threshold must be between 0 and 100.")

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                s.topic,
                f.recorded_at,
                f.reach,
                f.likes,
                f.shares,
                f.saves,
                f.comments,
                f.is_simulated
            FROM approved_scripts AS s
            JOIN performance_feedback AS f
                ON s.script_id = f.script_id
            WHERE s.account_id = ?
              AND s.approved = 1
              AND f.reach > 0
            ORDER BY f.recorded_at DESC, f.feedback_id DESC
            LIMIT ?
            """,
            (account_id, recent_limit),
        ).fetchall()

    groups = {}

    for row in rows:
        feedback_type = (
            "simulated" if row["is_simulated"] else "real"
        )
        topic_key = (row["topic"], feedback_type)

        interactions = (
            row["likes"]
            + row["shares"]
            + row["saves"]
            + row["comments"]
        )
        engagement_rate = interactions / row["reach"] * 100

        groups.setdefault(topic_key, []).append({
            "recorded_at": row["recorded_at"],
            "engagement_rate": round(engagement_rate, 2),
        })

    candidates = []

    for (topic, feedback_type), records in groups.items():
        if len(records) < 2:
            continue

        latest = records[0]["engagement_rate"]
        previous = records[1]["engagement_rate"]

        decline = (
            round((previous - latest) / previous * 100, 2)
            if previous > 0
            else 0.0
        )

        candidates.append({
            "topic": topic,
            "feedback_type": feedback_type,
            "feedback_count": len(records),
            "latest_engagement_rate": latest,
            "previous_engagement_rate": previous,
            "engagement_decline_percent": decline,
            "repeated_recently": True,
            "possible_performance_decline": (
                decline >= decline_threshold
            ),
            "fatigue_candidate": decline >= decline_threshold,
        })

    return {
        "account_id": account_id,
        "feedback_records_checked": len(rows),
        "fatigue_candidates": candidates,
        "note": (
            "Real and simulated feedback are analysed separately. "
            "A decline is a screening signal, not causal proof "
            "of audience fatigue."
        ),
    }