"""
Tests for the cleaning pipeline.
"""

from src.analysis.cleaning import (
    clean_text,
    detect_neighborhoods,
    detect_phase,
    flag_quality,
)


class TestCleanText:
    def test_strips_urls(self):
        text = "Check this out https://example.com/page and www.test.com"
        result = clean_text(text)
        assert "https://" not in result
        assert "www." not in result

    def test_strips_usernames(self):
        assert "@user123" not in clean_text("Thanks @user123 for sharing this to everyone")
        assert "u/reddituser" not in clean_text("As u/reddituser said about this topic")

    def test_strips_deleted(self):
        assert "[deleted]" not in clean_text("[deleted] was here and said things")
        assert "[removed]" not in clean_text("This was [removed] from the thread entirely")

    def test_hashtag_to_word(self):
        result = clean_text("Love #SouthShore community so much today")
        assert "SouthShore" in result
        assert "#" not in result

    def test_empty_input(self):
        assert clean_text("") == ""
        assert clean_text(None) == ""

    def test_short_text_filtered(self):
        assert clean_text("Hi") == ""

    def test_markdown_links(self):
        result = clean_text("See [this article](https://example.com) for more details today")
        assert "this article" in result
        assert "https://" not in result


class TestDetectPhase:
    def test_pre_phase(self):
        assert detect_phase("2025-09-20T12:00:00+00:00") == "pre"

    def test_event_phase(self):
        assert detect_phase("2025-09-30T12:00:00+00:00") == "event"

    def test_post_week1(self):
        assert detect_phase("2025-10-03T12:00:00+00:00") == "post_week1"

    def test_court_action(self):
        assert detect_phase("2025-11-15T12:00:00+00:00") == "court_action"

    def test_displacement(self):
        assert detect_phase("2025-12-01T12:00:00+00:00") == "displacement"

    def test_out_of_window(self):
        assert detect_phase("2025-12-25T12:00:00+00:00") == "outside_window"


class TestDetectNeighborhoods:
    def test_south_shore(self):
        hoods = detect_neighborhoods("The raid happened in South Shore near 71st")
        assert "South Shore" in hoods

    def test_multiple(self):
        hoods = detect_neighborhoods("South Shore and Woodlawn are affected")
        assert "South Shore" in hoods
        assert "Woodlawn" in hoods

    def test_no_match(self):
        assert detect_neighborhoods("Random text with no neighborhood") == []

    def test_empty(self):
        assert detect_neighborhoods("") == []


class TestFlagQuality:
    def test_ok(self):
        assert flag_quality("This is a normal post about the community", 8) == "ok"

    def test_short(self):
        assert flag_quality("Hi", 1) == "short"

    def test_spam(self):
        assert flag_quality("Buy now http://a http://b http://c http://d", 6) == "spam"
