
import pytest

from src.analytics.performance import calculate_post_metrics


@pytest.fixture
def sample_post():
    return {
        "post_id": "test_001",
        "topic": "Test topic",
        "content_bucket": "Economy",
        "hook_style": "Question",
        "format": "Explainer Reel",
        "reach": 10000,
        "views": 12000,
        "duration_seconds": 50,
        "likes": 500,
        "comments": 100,
        "shares": 200,
        "saves": 300,
        "watch_time_avg_seconds": 25,
        "followers_gained": 50,
    }


def test_calculate_post_metrics(sample_post):
    result = calculate_post_metrics(sample_post)

    assert result["interactions"] == 1100
    assert result["engagement_rate"] == 11.0
    assert result["share_rate"] == 2.0
    assert result["save_rate"] == 3.0
    assert result["average_watch_ratio"] == 50.0
    assert result["follower_conversion_rate"] == 0.5
    assert result["view_to_reach_ratio"] == 1.2


def test_zero_reach_rejected(sample_post):
    sample_post["reach"] = 0

    with pytest.raises(ValueError):
        calculate_post_metrics(sample_post)


def test_negative_values_rejected(sample_post):
    sample_post["shares"] = -5

    with pytest.raises(ValueError):
        calculate_post_metrics(sample_post)