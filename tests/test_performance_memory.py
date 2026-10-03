
import sqlite3

import pytest

import src.memory.performance_memory as memory


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Create a temporary database for isolated tests."""
    db_path = tmp_path / "test_memory.db"

    def test_connection():
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    with test_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE accounts (
                account_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                platform TEXT NOT NULL,
                language TEXT NOT NULL,
                profile_json TEXT NOT NULL
            );

            CREATE TABLE approved_scripts (
                script_id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                topic TEXT NOT NULL,
                content_bucket TEXT NOT NULL,
                hook_style TEXT NOT NULL,
                format TEXT NOT NULL,
                tone TEXT NOT NULL,
                strategy_json TEXT NOT NULL,
                script_text TEXT NOT NULL,
                critic_score REAL,
                approved INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (account_id)
                    REFERENCES accounts(account_id)
            );

            CREATE TABLE performance_feedback (
                feedback_id TEXT PRIMARY KEY,
                script_id TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                views INTEGER NOT NULL,
                reach INTEGER NOT NULL,
                likes INTEGER NOT NULL,
                shares INTEGER NOT NULL,
                saves INTEGER NOT NULL,
                comments INTEGER NOT NULL,
                watch_time_avg_seconds REAL NOT NULL,
                followers_gained INTEGER NOT NULL,
                is_simulated INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (script_id)
                    REFERENCES approved_scripts(script_id)
            );

            INSERT INTO accounts VALUES (
                'test_account', 'Test', 'Instagram',
                'Hinglish', '{}'
            );
            """
        )

    monkeypatch.setattr(memory, "get_connection", test_connection)
    return test_connection


def test_save_and_retrieve_approved_script(test_db):
    script_id = memory.save_approved_script(
        account_id="test_account",
        topic="Test topic",
        content_bucket="Economy",
        hook_style="Curiosity",
        format="Documentary Reel",
        tone="Hinglish",
        strategy={"confidence": 0.8},
        script_text="A sample test script.",
        critic_score=9.0,
    )

    recent = memory.get_recent_content("test_account")

    assert len(recent) == 1
    assert recent[0]["script_id"] == script_id
    assert recent[0]["topic"] == "Test topic"


def test_feedback_is_stored_as_simulated(test_db):
    script_id = memory.save_approved_script(
        account_id="test_account",
        topic="Test topic",
        content_bucket="Economy",
        hook_style="Curiosity",
        format="Documentary Reel",
        tone="Hinglish",
        strategy={},
        script_text="A sample test script.",
        critic_score=9.0,
    )

    memory.record_performance_feedback(
        script_id=script_id,
        metrics={
            "views": 5000,
            "reach": 4000,
            "likes": 300,
            "shares": 100,
            "saves": 80,
            "comments": 20,
            "watch_time_avg_seconds": 20,
            "followers_gained": 15,
        },
        is_simulated=True,
    )

    result = memory.get_performance_patterns("test_account")

    assert len(result["patterns"]) == 1
    assert result["patterns"][0]["feedback_type"] == "simulated"
    assert result["patterns"][0]["engagement_rate"] == 12.5


def test_invalid_reach_is_rejected(test_db):
    script_id = memory.save_approved_script(
        account_id="test_account",
        topic="Test topic",
        content_bucket="Economy",
        hook_style="Curiosity",
        format="Documentary Reel",
        tone="Hinglish",
        strategy={},
        script_text="A sample test script.",
        critic_score=9.0,
    )

    metrics = {
        "views": 100,
        "reach": 0,
        "likes": 10,
        "shares": 2,
        "saves": 3,
        "comments": 1,
        "watch_time_avg_seconds": 10,
        "followers_gained": 1,
    }

    with pytest.raises(ValueError, match="Reach must be greater"):
        memory.record_performance_feedback(
            script_id=script_id,
            metrics=metrics,
        )