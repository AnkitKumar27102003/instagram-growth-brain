
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