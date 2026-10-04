
from typing import Any
from statistics import mean

from src.memory.database import get_connection


def calculate_post_metrics(post: Any) -> dict:
    """Calculate descriptive performance metrics for one Reel."""

    reach = post["reach"]
    views = post["views"]
    duration = post["duration_seconds"]
    likes = post["likes"]
    comments = post["comments"]
    shares = post["shares"]
    saves = post["saves"]
    followers = post["followers_gained"]
    watch_time = post["watch_time_avg_seconds"]

    if reach <= 0:
        raise ValueError("Reach must be greater than zero.")

    if duration <= 0:
        raise ValueError("Duration must be greater than zero.")

    if min(
        views, likes, comments, shares, saves,
        followers, watch_time
    ) < 0:
        raise ValueError("Performance values cannot be negative.")

    interactions = likes + comments + shares + saves

    return {
        "post_id": post["post_id"],
        "topic": post["topic"],
        "content_bucket": post["content_bucket"],
        "hook_style": post["hook_style"],
        "format": post["format"],
        "reach": reach,
        "views": views,
        "interactions": interactions,
        "engagement_rate": round(interactions / reach * 100, 2),
        "share_rate": round(shares / reach * 100, 2),
        "save_rate": round(saves / reach * 100, 2),
        "average_watch_ratio": round(
            watch_time / duration * 100, 2
        ),
        "follower_conversion_rate": round(
            followers / reach * 100, 2
        ),
        "view_to_reach_ratio": round(views / reach, 2),
    }


def analyze_account() -> dict:
    """Analyze all posts stored in the local SQLite database."""

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM posts
            ORDER BY published_at ASC
            """
        ).fetchall()

    posts = [dict(row) for row in rows]

    if not posts:
        return {
            "post_count": 0,
            "average_metrics": {},
            "topic_performance": {},
            "post_metrics": [],
        }

    post_metrics = [
        calculate_post_metrics(post)
        for post in posts
    ]

    metric_names = [
        "engagement_rate",
        "share_rate",
        "save_rate",
        "average_watch_ratio",
        "follower_conversion_rate",
        "view_to_reach_ratio",
    ]

    average_metrics = {
        metric: round(
            mean(post[metric] for post in post_metrics), 2
        )
        for metric in metric_names
    }

    topic_groups = {}

    for post in post_metrics:
        topic = post["topic"]
        topic_groups.setdefault(topic, []).append(post)

    topic_performance = {}

    for topic, topic_posts in topic_groups.items():
        topic_performance[topic] = {
            "post_count": len(topic_posts),
            "average_engagement_rate": round(
                mean(p["engagement_rate"] for p in topic_posts), 2
            ),
            "average_share_rate": round(
                mean(p["share_rate"] for p in topic_posts), 2
            ),
            "average_watch_ratio": round(
                mean(p["average_watch_ratio"] for p in topic_posts), 2
            ),
            "total_reach": sum(p["reach"] for p in topic_posts),
        }

    return {
        "post_count": len(post_metrics),
        "average_metrics": average_metrics,
        "topic_performance": topic_performance,
        "post_metrics": post_metrics,
    }


def detect_breakout_content(
    account_id: str,
    min_feedback_records: int = 3,
    breakout_multiplier: float = 1.5,
) -> dict:
    """
    Identify approved scripts with unusually high engagement.

    Real and simulated feedback are evaluated separately.
    A breakout is a performance signal, not proof of virality.
    """

    if not account_id or not account_id.strip():
        raise ValueError("account_id must not be empty.")

    if min_feedback_records < 2:
        raise ValueError(
            "min_feedback_records must be at least 2."
        )

    if breakout_multiplier <= 1:
        raise ValueError(
            "breakout_multiplier must be greater than 1."
        )

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                s.script_id,
                s.topic,
                s.content_bucket,
                s.hook_style,
                s.format,
                s.tone,
                f.feedback_id,
                f.recorded_at,
                f.reach,
                f.likes,
                f.shares,
                f.saves,
                f.comments,
                f.watch_time_avg_seconds,
                f.is_simulated
            FROM approved_scripts AS s
            JOIN performance_feedback AS f
                ON s.script_id = f.script_id
            WHERE
                s.account_id = ?
                AND s.approved = 1
                AND f.reach > 0
            ORDER BY f.recorded_at DESC, f.feedback_id DESC
            """,
            (account_id,),
        ).fetchall()

    feedback_rows = [dict(row) for row in rows]

    result = {
        "account_id": account_id,
        "feedback_records_checked": len(feedback_rows),
        "minimum_feedback_records": min_feedback_records,
        "breakout_multiplier": breakout_multiplier,
        "real": {
            "feedback_records_checked": 0,
            "baseline_engagement_rate": 0.0,
            "breakout_candidates": [],
            "successful_patterns": [],
        },
        "simulated": {
            "feedback_records_checked": 0,
            "baseline_engagement_rate": 0.0,
            "breakout_candidates": [],
            "successful_patterns": [],
        },
        "note": (
            "Breakout detection compares engagement within the same "
            "feedback type. Simulated results are not real audience "
            "performance. A breakout is a screening signal, not "
            "proof of virality or causation."
        ),
    }

    # Keep real and simulated data separate.
    for feedback_type, is_simulated in (
        ("real", 0),
        ("simulated", 1),
    ):
        records = [
            row for row in feedback_rows
            if bool(row["is_simulated"]) == bool(is_simulated)
        ]

        result[feedback_type]["feedback_records_checked"] = len(
            records
        )

        if len(records) < min_feedback_records:
            continue

        # Aggregate multiple feedback records for each script,
        # so scripts with repeated measurements do not dominate
        # the account-level baseline.
        script_groups = {}

        for row in records:
            interactions = (
                row["likes"]
                + row["shares"]
                + row["saves"]
                + row["comments"]
            )

            engagement_rate = (
                interactions / row["reach"] * 100
            )

            script_id = row["script_id"]

            script_groups.setdefault(script_id, []).append({
                "row": row,
                "engagement_rate": engagement_rate,
            })

        script_metrics = []

        for script_id, measurements in script_groups.items():
            latest = measurements[0]
            metadata = latest["row"]

            avg_engagement = mean(
                item["engagement_rate"]
                for item in measurements
            )

            avg_share_rate = mean(
                item["row"]["shares"] / item["row"]["reach"] * 100
                for item in measurements
            )

            avg_save_rate = mean(
                item["row"]["saves"] / item["row"]["reach"] * 100
                for item in measurements
            )

            avg_watch_time = mean(
                item["row"]["watch_time_avg_seconds"]
                for item in measurements
            )

            script_metrics.append({
                "script_id": script_id,
                "topic": metadata["topic"],
                "content_bucket": metadata["content_bucket"],
                "hook_style": metadata["hook_style"],
                "format": metadata["format"],
                "tone": metadata["tone"],
                "feedback_count": len(measurements),
                "engagement_rate": avg_engagement,
                "share_rate": avg_share_rate,
                "save_rate": avg_save_rate,
                "average_watch_time_seconds": avg_watch_time,
                "latest_recorded_at": metadata["recorded_at"],
            })

        # Require enough distinct scripts to create a baseline.
        if len(script_metrics) < min_feedback_records:
            continue

        baseline = mean(
            item["engagement_rate"]
            for item in script_metrics
        )

        result[feedback_type]["baseline_engagement_rate"] = round(
            baseline, 2
        )

        if baseline <= 0:
            continue

        threshold = baseline * breakout_multiplier

        candidates = []

        for item in script_metrics:
            if item["engagement_rate"] < threshold:
                continue

            candidate = {
                **item,
                "engagement_rate": round(
                    item["engagement_rate"], 2
                ),
                "share_rate": round(item["share_rate"], 2),
                "save_rate": round(item["save_rate"], 2),
                "average_watch_time_seconds": round(
                    item["average_watch_time_seconds"], 2
                ),
                "baseline_engagement_rate": round(baseline, 2),
                "performance_lift": round(
                    item["engagement_rate"] / baseline, 2
                ),
                "breakout_candidate": True,
                "feedback_type": feedback_type,
            }

            candidates.append(candidate)

        candidates.sort(
            key=lambda item: item["performance_lift"],
            reverse=True,
        )

        # Summarize patterns in breakout candidates. These are
        # observations to inform future strategy, not instructions
        # to copy the exact topic or script.
        pattern_counts = {}

        for candidate in candidates:
            for field in (
                "content_bucket",
                "hook_style",
                "format",
            ):
                value = candidate[field]

                if not value:
                    continue

                pattern_key = (field, value)
                pattern_counts[pattern_key] = (
                    pattern_counts.get(pattern_key, 0) + 1
                )

        successful_patterns = [
            {
                "pattern_type": field,
                "value": value,
                "breakout_count": count,
            }
            for (field, value), count in pattern_counts.items()
        ]

        successful_patterns.sort(
            key=lambda item: item["breakout_count"],
            reverse=True,
        )

        result[feedback_type]["breakout_candidates"] = candidates
        result[feedback_type]["successful_patterns"] = (
            successful_patterns
        )

    return result
