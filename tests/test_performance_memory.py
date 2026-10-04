
import sqlite3

import pytest
import src.analytics.fatigue as fatigue
import src.analytics.performance as performance
import src.memory.performance_memory as memory

from src.analytics.fatigue import detect_feedback_topic_fatigue
from src.analytics.performance import detect_breakout_content


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
    monkeypatch.setattr(fatigue, "get_connection", test_connection)
    monkeypatch.setattr(performance, "get_connection", test_connection)

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


def create_script(topic="Test topic"):
    return memory.save_approved_script(
        account_id="test_account",
        topic=topic,
        content_bucket="Economy",
        hook_style="Curiosity",
        format="Documentary Reel",
        tone="Hinglish",
        strategy={},
        script_text="A sample test script.",
        critic_score=9.0,
    )


def create_metrics(reach, likes, shares=0, saves=0, comments=0):
    return {
        "views": reach,
        "reach": reach,
        "likes": likes,
        "shares": shares,
        "saves": saves,
        "comments": comments,
        "watch_time_avg_seconds": 10,
        "followers_gained": 0,
    }


def add_feedback(
    script_id,
    reach,
    likes,
    is_simulated=True,
    shares=0,
    saves=0,
    comments=0,
):
    """Store one feedback record for a script."""
    return memory.record_performance_feedback(
        script_id=script_id,
        metrics=create_metrics(
            reach=reach,
            likes=likes,
            shares=shares,
            saves=saves,
            comments=comments,
        ),
        is_simulated=is_simulated,
    )


def test_feedback_fatigue_detects_engagement_decline(test_db):
    script_id = create_script("Monsoon impact")

    memory.record_performance_feedback(
        script_id,
        create_metrics(1000, 200),
        is_simulated=True,
    )
    memory.record_performance_feedback(
        script_id,
        create_metrics(1000, 100),
        is_simulated=True,
    )

    result = detect_feedback_topic_fatigue("test_account")

    candidate = result["fatigue_candidates"][0]
    assert candidate["topic"] == "Monsoon impact"
    assert candidate["feedback_type"] == "simulated"
    assert candidate["engagement_decline_percent"] == 50.0
    assert candidate["fatigue_candidate"] is True


def test_feedback_fatigue_keeps_real_and_simulated_separate(test_db):
    script_id = create_script("Oil prices")

    memory.record_performance_feedback(
        script_id,
        create_metrics(1000, 200),
        is_simulated=True,
    )
    memory.record_performance_feedback(
        script_id,
        create_metrics(1000, 50),
        is_simulated=False,
    )

    result = detect_feedback_topic_fatigue("test_account")

    assert result["fatigue_candidates"] == []


def test_feedback_fatigue_ignores_single_record(test_db):
    script_id = create_script("Agriculture")

    memory.record_performance_feedback(
        script_id,
        create_metrics(1000, 200),
        is_simulated=True,
    )

    result = detect_feedback_topic_fatigue("test_account")

    assert result["fatigue_candidates"] == []


def test_breakout_detects_high_performing_script(test_db):
    scripts = [
        create_script("Oil prices"),
        create_script("Inflation"),
        create_script("Monsoon"),
        create_script("Rupee depreciation"),
    ]

    for script_id in scripts[:3]:
        add_feedback(script_id, reach=1000, likes=50)

    add_feedback(
        scripts[3],
        reach=1000,
        likes=400,
        shares=50,
        saves=50,
    )

    result = detect_breakout_content("test_account")

    simulated = result["simulated"]
    candidates = simulated["breakout_candidates"]

    assert len(candidates) == 1
    assert candidates[0]["topic"] == "Rupee depreciation"
    assert candidates[0]["feedback_type"] == "simulated"
    assert candidates[0]["breakout_candidate"] is True
    assert candidates[0]["engagement_rate"] == 50.0
    assert candidates[0]["performance_lift"] > 1.5
    assert simulated["baseline_engagement_rate"] > 0


def test_breakout_keeps_real_and_simulated_feedback_separate(test_db):
    scripts = [
        create_script("Oil prices"),
        create_script("Inflation"),
        create_script("Monsoon"),
        create_script("Rupee depreciation"),
    ]

    for script_id in scripts:
        add_feedback(
            script_id,
            reach=1000,
            likes=50,
            is_simulated=False,
        )

    for script_id in scripts[:3]:
        add_feedback(
            script_id,
            reach=1000,
            likes=50,
            is_simulated=True,
        )

    add_feedback(
        scripts[3],
        reach=1000,
        likes=400,
        shares=50,
        saves=50,
        is_simulated=True,
    )

    result = detect_breakout_content("test_account")

    assert result["real"]["breakout_candidates"] == []
    assert len(result["simulated"]["breakout_candidates"]) == 1

    assert result["real"]["feedback_records_checked"] == 4
    assert result["simulated"]["feedback_records_checked"] == 4


def test_breakout_requires_enough_distinct_scripts(test_db):
    scripts = [
        create_script("Oil prices"),
        create_script("Inflation"),
    ]

    for script_id in scripts:
        add_feedback(script_id, reach=1000, likes=100)

    result = detect_breakout_content(
        "test_account",
        min_feedback_records=3,
    )

    assert result["simulated"]["breakout_candidates"] == []
    assert result["simulated"]["baseline_engagement_rate"] == 0.0


@pytest.mark.parametrize(
    "kwargs, error_message",
    [
        (
            {"account_id": ""},
            "account_id must not be empty",
        ),
        (
            {"account_id": "test_account", "min_feedback_records": 1},
            "min_feedback_records must be at least 2",
        ),
        (
            {"account_id": "test_account", "breakout_multiplier": 1.0},
            "breakout_multiplier must be greater than 1",
        ),
    ],
)
def test_breakout_rejects_invalid_parameters(
    test_db,
    kwargs,
    error_message,
):
    with pytest.raises(ValueError, match=error_message):
        detect_breakout_content(**kwargs)
