"""
Ingestion Pipeline Orchestrator.

Orchestrates data collection from all sources (Reddit, News, YouTube),
normalizes to common schema, deduplicates, and stores to DuckDB + Parquet.
"""

import argparse
from collections import Counter

import pandas as pd

from src.ingestion.news_collector import NewsCollector
from src.ingestion.reddit_collector import collect_reddit_data
from src.ingestion.synthetic_generator import generate_synthetic_data
from src.utils.constants import PROJECT_ROOT
from src.utils.db import get_connection, init_database
from src.utils.logger import log


def ingest_live() -> pd.DataFrame:
    """Collect data from live sources (Reddit + News + YouTube)."""
    all_posts = []

    # ── Reddit (PullPush + Old Reddit) ───────────────────
    log.info("=" * 60)
    log.info("Phase 1: Collecting Reddit data via PullPush.io + Old Reddit")
    log.info("=" * 60)
    try:
        reddit_posts = collect_reddit_data(method="both")
        all_posts.extend(reddit_posts)
        log.info(f"Reddit: {len(reddit_posts)} posts collected")
    except Exception as e:
        log.error(f"Reddit collection failed: {e}")
        log.info("Falling back to Old Reddit only...")
        try:
            reddit_posts = collect_reddit_data(method="old_reddit")
            all_posts.extend(reddit_posts)
        except Exception as e2:
            log.error(f"Old Reddit fallback also failed: {e2}")

    # ── News Comments ────────────────────────────────────
    log.info("=" * 60)
    log.info("Phase 2: Collecting news comments")
    log.info("=" * 60)
    try:
        news_collector = NewsCollector()
        news_posts = news_collector.collect_all()
        all_posts.extend(news_posts)
        log.info(f"News: {len(news_posts)} items collected")
    except Exception as e:
        log.error(f"News collection failed: {e}")

    # ── YouTube (Data API v3) ────────────────────────────
    log.info("=" * 60)
    log.info("Phase 3: Collecting YouTube videos + comments")
    log.info("=" * 60)
    try:
        from src.ingestion.youtube_collector import collect_youtube_data

        youtube_posts = collect_youtube_data()
        all_posts.extend(youtube_posts)
        log.info(f"YouTube: {len(youtube_posts)} items collected")
    except Exception as e:
        log.error(f"YouTube collection failed: {e}")

    df = pd.DataFrame(all_posts)

    # Log platform breakdown
    if not df.empty:
        platform_counts = Counter(df["platform"])
        log.info(f"Platform breakdown: {dict(platform_counts)}")

    log.info(f"Total live posts: {len(df)}")
    return df


def ingest_synthetic(n_posts: int = 3500) -> pd.DataFrame:
    """Generate synthetic fallback data."""
    log.info("=" * 60)
    log.info(f"Generating {n_posts} synthetic posts")
    log.info("=" * 60)

    posts = generate_synthetic_data(n_posts=n_posts)
    df = pd.DataFrame(posts)
    log.info(f"Synthetic posts generated: {len(df)}")
    return df


def store_to_db(df: pd.DataFrame) -> None:
    """Store DataFrame to DuckDB posts_raw table."""
    if df.empty:
        log.warning("No data to store")
        return

    conn = get_connection()

    # Ensure columns match schema
    expected_cols = [
        "id",
        "platform",
        "source",
        "url",
        "dt_utc",
        "text",
        "title",
        "author_display",
        "score",
        "like_count",
        "reply_count",
        "share_count",
        "parent_id",
        "post_type",
        "detected_locs",
        "anchors",
        "search_term",
    ]

    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    df = df[expected_cols].copy()

    # Convert dt_utc to proper timestamp
    df["dt_utc"] = pd.to_datetime(df["dt_utc"], utc=True, format="mixed")

    # Deduplicate by id
    df = df.drop_duplicates(subset=["id"], keep="first")

    # Insert using DuckDB's DataFrame registration
    conn.execute("DELETE FROM posts_raw")  # Clear for fresh ingestion
    conn.register("df_posts", df)
    conn.execute("""
        INSERT INTO posts_raw (
            id, platform, source, url, dt_utc, text, title,
            author_display, score, like_count, reply_count, share_count,
            parent_id, post_type, detected_locs, anchors, search_term
        )
        SELECT
            id, platform, source, url, dt_utc, text, title,
            author_display, score, like_count, reply_count, share_count,
            parent_id, post_type, detected_locs, anchors, search_term
        FROM df_posts
    """)

    count = conn.execute("SELECT COUNT(*) FROM posts_raw").fetchone()[0]

    # Log platform breakdown in DB
    plat_df = conn.execute(
        "SELECT platform, COUNT(*) as n FROM posts_raw GROUP BY platform"
    ).fetchdf()
    log.info(f"Stored {count} posts in posts_raw")
    log.info(f"DB platform breakdown:\n{plat_df.to_string(index=False)}")

    conn.close()


def export_parquet(df: pd.DataFrame, name: str = "posts_raw") -> None:
    """Export DataFrame as Parquet file."""
    raw_dir = PROJECT_ROOT / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{name}.parquet"
    df.to_parquet(path, index=False)
    log.info(f"Exported to {path}")


def run_pipeline(mode: str = "synthetic", n_posts: int = 3500):
    """Run the full ingestion pipeline."""
    log.info("🚀 Starting ingestion pipeline")
    log.info(f"Mode: {mode}")

    # Initialize DB
    init_database()

    # Collect data
    if mode == "live":
        df = ingest_live()
        # If live collection yields too few results, supplement with synthetic
        if len(df) < 100:
            log.warning(f"Only {len(df)} live posts. Supplementing with synthetic data.")
            df_syn = ingest_synthetic(n_posts=n_posts - len(df))
            df = pd.concat([df, df_syn], ignore_index=True)
    elif mode == "synthetic":
        df = ingest_synthetic(n_posts=n_posts)
    elif mode == "both":
        df_live = ingest_live()
        df_syn = ingest_synthetic(n_posts=max(500, n_posts - len(df_live)))
        df = pd.concat([df_live, df_syn], ignore_index=True)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    # Store and export
    store_to_db(df)
    export_parquet(df, "posts_raw")

    log.info(f"✅ Ingestion complete: {len(df)} total posts")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="South Shore Sentiment Study — Data Ingestion")
    parser.add_argument(
        "--mode",
        choices=["live", "synthetic", "both"],
        default="synthetic",
        help="Collection mode: live, synthetic, or both",
    )
    parser.add_argument(
        "--n-posts", type=int, default=3500, help="Number of synthetic posts to generate"
    )
    args = parser.parse_args()

    run_pipeline(mode=args.mode, n_posts=args.n_posts)
