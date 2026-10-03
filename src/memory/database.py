
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "instagram_growth.db"


def get_connection():
    """Create a connection to the local SQLite database."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database():
    """Create the database tables if they don't exist."""

    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                account_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                platform TEXT NOT NULL,
                language TEXT NOT NULL,
                profile_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS posts (
                post_id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                published_at TEXT NOT NULL,
                topic TEXT NOT NULL,
                content_bucket TEXT NOT NULL,
                hook_style TEXT NOT NULL,
                format TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                views INTEGER NOT NULL,
                reach INTEGER NOT NULL,
                likes INTEGER NOT NULL,
                shares INTEGER NOT NULL,
                saves INTEGER NOT NULL,
                comments INTEGER NOT NULL,
                watch_time_avg_seconds REAL NOT NULL,
                followers_gained INTEGER NOT NULL,
                FOREIGN KEY (account_id)
                    REFERENCES accounts(account_id)
            );

            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                event_date TEXT NOT NULL,
                category TEXT NOT NULL,
                relevance REAL NOT NULL,
                source_url TEXT,
                source_name TEXT,
                verified_at TEXT,
                verification_status TEXT NOT NULL,
                suggested_content_bucket TEXT
            );

            CREATE TABLE IF NOT EXISTS competitors (
                competitor_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                platform TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS competitor_posts (
                post_id TEXT PRIMARY KEY,
                competitor_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                hook_style TEXT NOT NULL,
                format TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                views INTEGER NOT NULL,
                shares INTEGER NOT NULL,
                observed_at TEXT NOT NULL,
                FOREIGN KEY (competitor_id)
                    REFERENCES competitors(competitor_id)
            );

            CREATE INDEX IF NOT EXISTS idx_posts_topic
                ON posts(topic);

            CREATE INDEX IF NOT EXISTS idx_posts_published
                ON posts(published_at);

            CREATE INDEX IF NOT EXISTS idx_events_date
                ON events(event_date);
            """
        )

    print(f"Database initialized: {DATABASE_PATH}")


if __name__ == "__main__":
    initialize_database()