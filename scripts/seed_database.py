
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.memory.database import (
    get_connection,
    initialize_database,
)

DATA_DIR = PROJECT_ROOT / "data"


def load_json(filename):
    """Load a JSON file from the data directory."""
    file_path = DATA_DIR / filename

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def seed_database():
    """Load all sample datasets into SQLite."""
    account_data = load_json("account.json")
    posts_data = load_json("posts.json")
    events_data = load_json("events.json")
    competitors_data = load_json("competitors.json")

    initialize_database()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO accounts
            (account_id, name, platform, language, profile_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                account_data["account_id"],
                account_data["name"],
                account_data["platform"],
                account_data["language"],
                json.dumps(account_data),
            ),
        )

        for post in posts_data["posts"]:
            connection.execute(
                """
                INSERT OR REPLACE INTO posts VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    post["post_id"],
                    posts_data["account_id"],
                    post["published_at"],
                    post["topic"],
                    post["content_bucket"],
                    post["hook_style"],
                    post["format"],
                    post["duration_seconds"],
                    post["views"],
                    post["reach"],
                    post["likes"],
                    post["shares"],
                    post["saves"],
                    post["comments"],
                    post["watch_time_avg_seconds"],
                    post["followers_gained"],
                ),
            )

        for event in events_data["events"]:
            connection.execute(
                """
                INSERT OR REPLACE INTO events VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    event["event_id"],
                    event["name"],
                    event["event_date"],
                    event["category"],
                    event["relevance"],
                    event["source_url"],
                    event["source_name"],
                    event["verified_at"],
                    event["verification_status"],
                    event["suggested_content_bucket"],
                ),
            )

        for competitor in competitors_data["competitors"]:
            connection.execute(
                """
                INSERT OR REPLACE INTO competitors VALUES (?, ?, ?)
                """,
                (
                    competitor["competitor_id"],
                    competitor["name"],
                    competitor["platform"],
                ),
            )

            for post in competitor["posts"]:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO competitor_posts VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        post["post_id"],
                        competitor["competitor_id"],
                        post["topic"],
                        post["hook_style"],
                        post["format"],
                        post["duration_seconds"],
                        post["views"],
                        post["shares"],
                        post["observed_at"],
                    ),
                )

    print("Sample data seeded successfully!")


if __name__ == "__main__":
    seed_database()