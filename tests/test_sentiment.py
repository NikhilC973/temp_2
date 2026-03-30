"""
Tests for sentiment scoring.
"""


class TestVADER:
    def test_positive(self):
        from src.analysis.sentiment import score_vader

        result = score_vader("I love this community! Amazing people.")
        assert result["compound"] > 0.3

    def test_negative(self):
        from src.analysis.sentiment import score_vader

        result = score_vader("This is horrible and terrifying.")
        assert result["compound"] < -0.3

    def test_neutral(self):
        from src.analysis.sentiment import score_vader

        result = score_vader("The building is located on 71st street.")
        assert abs(result["compound"]) < 0.3

    def test_empty(self):
        from src.analysis.sentiment import score_vader

        result = score_vader("")
        assert result["compound"] == 0.0


class TestSentimentLabel:
    def test_positive_label(self):
        from src.analysis.sentiment import derive_sentiment_label

        assert derive_sentiment_label(0.5, 0.8, 0.1) == "positive"

    def test_negative_label(self):
        from src.analysis.sentiment import derive_sentiment_label

        assert derive_sentiment_label(-0.5, 0.1, 0.8) == "negative"

    def test_neutral_label(self):
        from src.analysis.sentiment import derive_sentiment_label

        assert derive_sentiment_label(0.0, 0.4, 0.4) == "neutral"
