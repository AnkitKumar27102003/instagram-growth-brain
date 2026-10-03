
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