"""
Tests for the ingestion pipeline.
"""

from src.ingestion.synthetic_generator import generate_synthetic_data
from src.utils.constants import PHASES


class TestSyntheticGenerator:
    def test_generates_correct_count(self):
        posts = generate_synthetic_data(n_posts=100, seed=42)
        assert len(posts) == 100

    def test_all_phases_represented(self):
        posts = generate_synthetic_data(n_posts=500, seed=42)
        phases = set(p["anchors"] for p in posts)
        for phase in PHASES:
            assert phase in phases, f"Phase {phase} missing from synthetic data"

    def test_all_three_platforms(self):
        posts = generate_synthetic_data(n_posts=500, seed=42)
        platforms = set(p["platform"] for p in posts)
        assert "reddit" in platforms
        assert "news_comment" in platforms
        assert "youtube" in platforms

    def test_unique_ids(self):
        posts = generate_synthetic_data(n_posts=200, seed=42)
        ids = [p["id"] for p in posts]
        assert len(ids) == len(set(ids)), "Duplicate IDs found"

    def test_has_required_fields(self):
        posts = generate_synthetic_data(n_posts=10, seed=42)
        required = ["id", "platform", "source", "dt_utc", "text", "post_type"]
        for post in posts:
            for field in required:
                assert field in post, f"Missing field: {field}"

    def test_deterministic_with_seed(self):
        posts_a = generate_synthetic_data(n_posts=50, seed=99)
        posts_b = generate_synthetic_data(n_posts=50, seed=99)
        assert [p["id"] for p in posts_a] == [p["id"] for p in posts_b]

    def test_youtube_post_types(self):
        posts = generate_synthetic_data(n_posts=500, seed=42)
        yt_posts = [p for p in posts if p["platform"] == "youtube"]
        assert len(yt_posts) > 0
        yt_types = set(p["post_type"] for p in yt_posts)
        assert "video" in yt_types
        assert "comment" in yt_types or "reply" in yt_types

    def test_youtube_video_engagement(self):
        posts = generate_synthetic_data(n_posts=500, seed=42)
        yt_videos = [p for p in posts if p["platform"] == "youtube" and p["post_type"] == "video"]
        if yt_videos:
            # Videos should have higher scores (view counts)
            avg_score = sum(v["score"] for v in yt_videos) / len(yt_videos)
            assert avg_score > 50, "YouTube video scores should represent view counts"
