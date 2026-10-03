
import json
import sqlite3
import uuid
from datetime import datetime, timezone

from src.memory.database import get_connection


def current_timestamp():
    """Return the current UTC time as an ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


def save_approved_script(
    account_id: str,
    topic: str,
    content_bucket: str,
    hook_style: str,
    format: str,
    tone: str,
    strategy: dict,
    script_text: str,
    critic_score: float,
    script_id: str | None = None,
) -> str:
    """Save an approved script and return its ID."""

    if not account_id.strip():
        raise ValueError("Account ID cannot be empty.")

    if not topic.strip() or not script_text.strip():
        raise ValueError("Topic and script text are required.")

    if not 0 <= critic_score <= 10:
        raise ValueError("Critic score must be between 0 and 10.")

    script_id = script_id or str(uuid.uuid4())

    connection = get_connection()
    try:
        connection.execute(
            """
            INSERT INTO approved_scripts (
                script_id, account_id, created_at, topic,
                content_bucket, hook_style, format, tone,
                strategy_json, script_text, critic_score, approved
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                script_id,
                account_id,
                current_timestamp(),
                topic,
                content_bucket,
                hook_style,
                format,
                tone,
                json.dumps(strategy, ensure_ascii=False),
                script_text,
                critic_score,
            ),
        )
        connection.commit()
    finally:
        connection.close()

    return script_id


def record_performance_feedback(
    script_id: str,
    metrics: dict,
    is_simulated: bool = True,
    feedback_id: str | None = None,
) -> str:
    """Store performance feedback for a saved script."""

    required_fields = [
        "views",
        "reach",
        "likes",
        "shares",
        "saves",
        "comments",
        "watch_time_avg_seconds",
        "followers_gained",
    ]

    missing = [
        field for field in required_fields
        if field not in metrics
    ]
    if missing:
        raise ValueError(
            f"Missing performance fields: {', '.join(missing)}"
        )

    for field in required_fields:
        if metrics[field] < 0:
            raise ValueError(
                f"{field} cannot be negative."
            )

    if metrics["reach"] <= 0:
        raise ValueError("Reach must be greater than zero.")

    if not isinstance(is_simulated, bool):
        raise ValueError("is_simulated must be True or False.")

    feedback_id = feedback_id or str(uuid.uuid4())

    connection = get_connection()
    try:
        connection.execute(
            """
            INSERT INTO performance_feedback (
                feedback_id, script_id, recorded_at,
                views, reach, likes, shares, saves, comments,
                watch_time_avg_seconds, followers_gained,
                is_simulated
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feedback_id,
                script_id,
                current_timestamp(),
                metrics["views"],
                metrics["reach"],
                metrics["likes"],
                metrics["shares"],
                metrics["saves"],
                metrics["comments"],
                metrics["watch_time_avg_seconds"],
                metrics["followers_gained"],
                int(is_simulated),
            ),
        )
        connection.commit()
    finally:
        connection.close()

    return feedback_id


def get_recent_content(account_id: str, limit: int = 10) -> list:
    """Retrieve recently approved scripts for an account."""

    if limit < 1:
        raise ValueError("Limit must be at least 1.")

    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT
                script_id, created_at, topic, content_bucket,
                hook_style, format, tone, critic_score
            FROM approved_scripts
            WHERE account_id = ? AND approved = 1
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (account_id, limit),
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_performance_patterns(account_id: str) -> dict:
    """
    Summarize historical performance by topic, hook and format.

    Metrics are calculated from recorded feedback. Simulated and
    real feedback are reported separately.
    """

    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT
                s.topic,
                s.hook_style,
                s.format,
                f.is_simulated,
                COUNT(*) AS feedback_count,
                SUM(f.reach) AS total_reach,
                SUM(f.likes + f.comments + f.shares + f.saves)
                    AS total_interactions,
                SUM(f.shares) AS total_shares,
                SUM(f.saves) AS total_saves,
                AVG(f.watch_time_avg_seconds)
                    AS average_watch_time
            FROM approved_scripts AS s
            JOIN performance_feedback AS f
                ON s.script_id = f.script_id
            WHERE s.account_id = ?
            GROUP BY
                s.topic, s.hook_style, s.format, f.is_simulated
            ORDER BY total_reach DESC
            """,
            (account_id,),
        ).fetchall()

        patterns = []
        for row in rows:
            item = dict(row)
            reach = item["total_reach"] or 0

            item["engagement_rate"] = round(
                item["total_interactions"] / reach * 100, 2
            ) if reach else 0

            item["share_rate"] = round(
                item["total_shares"] / reach * 100, 2
            ) if reach else 0

            item["save_rate"] = round(
                item["total_saves"] / reach * 100, 2
            ) if reach else 0

            item["feedback_type"] = (
                "simulated" if item["is_simulated"] else "real"
            )
            patterns.append(item)

        return {
            "account_id": account_id,
            "patterns": patterns,
            "note": (
                "Historical patterns are descriptive signals. "
                "Simulated results are not actual Instagram outcomes."
            ),
        }
    finally:
        connection.close()