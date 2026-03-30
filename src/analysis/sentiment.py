"""
Sentiment Analysis — VADER baseline + RoBERTa fine-tuned model.

VADER: Fast, lexicon-based polarity scoring.
RoBERTa: Transformer-based sentiment (positive/negative/neutral) fine-tuned on social media.
"""

from src.utils.constants import PROJECT_ROOT
from src.utils.db import get_connection, init_database
from src.utils.logger import log

# Lazy imports for heavy ML libraries
_vader_analyzer = None
_roberta_pipeline = None


def _get_vader():
    """Lazy-load VADER sentiment analyzer."""
    global _vader_analyzer
    if _vader_analyzer is None:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        _vader_analyzer = SentimentIntensityAnalyzer()
        log.info("VADER analyzer loaded")
    return _vader_analyzer


def _get_roberta():
    """Lazy-load RoBERTa sentiment pipeline."""
    global _roberta_pipeline
    if _roberta_pipeline is None:
        from transformers import pipeline

        _roberta_pipeline = pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment-latest",
            tokenizer="cardiffnlp/twitter-roberta-base-sentiment-latest",
            max_length=512,
            truncation=True,
            top_k=None,  # Return all labels with scores
        )
        log.info("RoBERTa sentiment pipeline loaded")
    return _roberta_pipeline


def score_vader(text: str) -> dict:
    """Get VADER polarity scores for a single text."""
    if not text or not isinstance(text, str):
        return {"compound": 0.0, "pos": 0.0, "neg": 0.0, "neu": 1.0}

    analyzer = _get_vader()
    scores = analyzer.polarity_scores(text)
    return {
        "compound": scores["compound"],
        "pos": scores["pos"],
        "neg": scores["neg"],
        "neu": scores["neu"],
    }


def score_roberta_batch(texts: list[str], batch_size: int = 32) -> list[dict]:
    """Score a batch of texts with RoBERTa. Returns list of {positive, negative, neutral}."""
    pipe = _get_roberta()
    results = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        # Clean empty texts
        batch_clean = [
            t if t and isinstance(t, str) and len(t.strip()) > 0 else "neutral" for t in batch
        ]

        try:
            preds = pipe(batch_clean)
            for pred in preds:
                score_dict = {"positive": 0.0, "negative": 0.0, "neutral": 0.0}
                if isinstance(pred, list):
                    for item in pred:
                        label = item["label"].lower()
                        if label in score_dict:
                            score_dict[label] = item["score"]
                results.append(score_dict)
        except Exception as e:
            log.warning(f"RoBERTa batch error: {e}")
            results.extend([{"positive": 0.0, "negative": 0.0, "neutral": 1.0}] * len(batch))

    return results


def derive_sentiment_label(vader_compound: float, roberta_pos: float, roberta_neg: float) -> str:
    """Derive overall sentiment label from combined scores."""
    vader_signal = 1 if vader_compound > 0.05 else (-1 if vader_compound < -0.05 else 0)
    roberta_signal = 1 if roberta_pos > roberta_neg else (-1 if roberta_neg > roberta_pos else 0)

    combined = vader_signal + roberta_signal
    if combined > 0:
        return "positive"
    elif combined < 0:
        return "negative"
    return "neutral"


def run_sentiment_analysis():
    """Run full sentiment scoring on posts_clean → posts_emotions (partial)."""
    log.info("📊 Starting sentiment analysis (VADER + RoBERTa)")

    init_database()
    conn = get_connection()

    # Load clean posts
    df = conn.execute("""
        SELECT id, text_clean
        FROM posts_clean
        WHERE is_duplicate = false AND quality_flag = 'ok'
    """).fetchdf()

    if df.empty:
        log.warning("No clean posts to analyze")
        conn.close()
        return

    log.info(f"Scoring {len(df)} posts")

    # VADER scoring
    log.info("Running VADER...")
    vader_scores = df["text_clean"].apply(score_vader)
    df["vader_compound"] = vader_scores.apply(lambda x: x["compound"])
    df["vader_positive"] = vader_scores.apply(lambda x: x["pos"])
    df["vader_negative"] = vader_scores.apply(lambda x: x["neg"])
    df["vader_neutral"] = vader_scores.apply(lambda x: x["neu"])

    # RoBERTa scoring
    log.info("Running RoBERTa...")
    texts = df["text_clean"].tolist()
    try:
        roberta_scores = score_roberta_batch(texts, batch_size=32)
        df["roberta_positive"] = [s["positive"] for s in roberta_scores]
        df["roberta_negative"] = [s["negative"] for s in roberta_scores]
        df["roberta_neutral"] = [s["neutral"] for s in roberta_scores]
    except Exception as e:
        log.warning(f"RoBERTa failed, using VADER only: {e}")
        df["roberta_positive"] = 0.0
        df["roberta_negative"] = 0.0
        df["roberta_neutral"] = 1.0

    # Derive label
    df["sentiment_label"] = df.apply(
        lambda row: derive_sentiment_label(
            row["vader_compound"], row["roberta_positive"], row["roberta_negative"]
        ),
        axis=1,
    )

    # Batch upsert to posts_emotions using DuckDB's DataFrame registration
    # Clear existing sentiment data and re-insert
    conn.execute("DELETE FROM posts_emotions")
    sentiment_df = df[
        [
            "id",
            "vader_compound",
            "vader_positive",
            "vader_negative",
            "vader_neutral",
            "roberta_positive",
            "roberta_negative",
            "roberta_neutral",
            "sentiment_label",
        ]
    ].copy()

    conn.register("df_sentiment", sentiment_df)
    conn.execute("""
        INSERT INTO posts_emotions (
            id, vader_compound, vader_positive, vader_negative, vader_neutral,
            roberta_positive, roberta_negative, roberta_neutral, sentiment_label
        )
        SELECT
            id, vader_compound, vader_positive, vader_negative, vader_neutral,
            roberta_positive, roberta_negative, roberta_neutral, sentiment_label
        FROM df_sentiment
    """)

    # Export
    processed_dir = PROJECT_ROOT / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(processed_dir / "sentiment_scores.parquet", index=False)

    # Stats
    label_dist = df["sentiment_label"].value_counts().to_dict()
    avg_compound = df["vader_compound"].mean()
    log.info("✅ Sentiment analysis complete")
    log.info(f"   Label distribution: {label_dist}")
    log.info(f"   Mean VADER compound: {avg_compound:.3f}")

    conn.close()


if __name__ == "__main__":
    run_sentiment_analysis()
