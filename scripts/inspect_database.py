
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.memory.database import get_connection


def inspect_database():
    with get_connection() as connection:
        tables = [
            "accounts",
            "posts",
            "events",
            "competitors",
            "competitor_posts",
        ]

        print("\nDATABASE SUMMARY")
        print("-" * 35)

        for table in tables:
            result = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()

            print(f"{table}: {result[0]} records")

        print("\nPOST PERFORMANCE")
        print("-" * 35)

        rows = connection.execute(
            """
            SELECT topic, views, shares, saves
            FROM posts
            ORDER BY views DESC
            """
        ).fetchall()

        for row in rows:
            print(
                f"{row['topic']}: "
                f"{row['views']:,} views, "
                f"{row['shares']:,} shares, "
                f"{row['saves']:,} saves"
            )


if __name__ == "__main__":
    inspect_database()