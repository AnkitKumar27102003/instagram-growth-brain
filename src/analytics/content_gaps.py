
import json
from collections import Counter
from pathlib import Path

from src.memory.database import get_connection

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def detect_content_gaps() -> dict:
    """Identify underused content buckets and formats."""

    with (PROJECT_ROOT / "data" / "account.json").open(
        "r", encoding="utf-8"
    ) as file:
        account = json.load(file)

    expected_buckets = account["content_buckets"]

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT content_bucket, format
            FROM posts
            ORDER BY published_at DESC
            """
        ).fetchall()

    bucket_counts = Counter(
        row["content_bucket"] for row in rows
    )
    format_counts = Counter(
        row["format"] for row in rows
    )

    total_posts = len(rows)

    bucket_analysis = {}

    for bucket in expected_buckets:
        count = bucket_counts.get(bucket, 0)

        bucket_analysis[bucket] = {
            "post_count": count,
            "share_of_posts": round(
                count / total_posts * 100, 2
            ) if total_posts else 0,
        }

    underrepresented_buckets = [
        bucket
        for bucket, data in bucket_analysis.items()
        if data["post_count"] == 0
    ]

    underused_buckets = [
        bucket
        for bucket, data in bucket_analysis.items()
        if 0 < data["post_count"] <= 1
    ]

    return {
        "total_posts": total_posts,
        "bucket_distribution": bucket_analysis,
        "underrepresented_buckets": underrepresented_buckets,
        "underused_buckets": underused_buckets,
        "format_distribution": dict(format_counts),
        "note": (
            "Content gaps indicate limited coverage in the "
            "sample history, not proof of audience demand."
        ),
    }