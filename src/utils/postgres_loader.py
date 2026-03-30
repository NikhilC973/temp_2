"""
PostgreSQL Loader — Transfers analyzed data from DuckDB into PostgreSQL star schema.

Usage:
    python -m src.utils.postgres_loader
    python -m src.utils.postgres_loader --pg-url postgresql://user:pass@localhost:5432/south_shore

Requires: pip install psycopg2-binary
"""

import os
import argparse
from datetime import date, timedelta

import pandas as pd

from src.utils.constants import PHASES, NEIGHBORHOOD_LEXICON, PLATFORMS
from src.utils.db import get_connection as get_duckdb
from src.utils.logger import log

DEFAULT_PG_URL = os.environ.get(
    "POSTGRES_URL",
    "postgresql://postgres:postgres@localhost:5432/south_shore",
)

PLATFORM_COLORS = {
    "reddit": "#FF4500",
    "youtube": "#FF0000",
    "news_comment": "#1DA1F2",
}

PLATFORM_DESCRIPTIONS = {
    "reddit": "14 subreddits including r/Chicago, r/news, r/immigration",
    "youtube": "YouTube video descriptions and comment threads",
    "news_comment": "Block Club Chicago, WBEZ, Sun-Times, South Side Weekly, AP",
}


def get_pg_connection(pg_url: str = DEFAULT_PG_URL):
    """Get a psycopg2 connection to PostgreSQL."""
    import psycopg2

    return psycopg2.connect(pg_url)


def create_schema(pg_url: str = DEFAULT_PG_URL) -> None:
    """Run the DDL script to create tables in PostgreSQL."""
    from pathlib import Path

    schema_path = Path(__file__).resolve().parents[2] / "sql" / "schema" / "01_create_tables.sql"

    if not schema_path.exists():
        log.error(f"Schema file not found: {schema_path}")
        log.info("Create sql/schema/01_create_tables.sql first (see strategic guide)")
        return

    conn = get_pg_connection(pg_url)
    cur = conn.cursor()
    cur.execute(schema_path.read_text())
    conn.commit()
    cur.close()
    conn.close()
    log.info("✅ PostgreSQL schema created")


def load_dim_platform(pg_url: str = DEFAULT_PG_URL) -> dict:
    """Load dim_platform and return {name: key} mapping."""
    conn = get_pg_connection(pg_url)
    cur = conn.cursor()

    for name in ["reddit", "youtube", "news_comment"]:
        cur.execute(
            """
            INSERT INTO dim_platform (platform_name, platform_color, description)
            VALUES (%s, %s, %s)
            ON CONFLICT (platform_name) DO NOTHING
        """,
            (name, PLATFORM_COLORS.get(name, "#888"), PLATFORM_DESCRIPTIONS.get(name, "")),
        )

    conn.commit()

    cur.execute("SELECT platform_name, platform_key FROM dim_platform")
    mapping = {row[0]: row[1] for row in cur.fetchall()}
    cur.close()
    conn.close()
    log.info(f"Loaded dim_platform: {mapping}")
    return mapping


def load_dim_phase(pg_url: str = DEFAULT_PG_URL) -> dict:
    """Load dim_phase and return {phase_id: key} mapping."""
    conn = get_pg_connection(pg_url)
    cur = conn.cursor()

    for order, (phase_id, info) in enumerate(PHASES.items(), 1):
        cur.execute(
            """
            INSERT INTO dim_phase (phase_id, phase_label, start_date, end_date, phase_order)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (phase_id) DO NOTHING
        """,
            (phase_id, info["label"], info["start"], info["end"], order),
        )

    conn.commit()

    cur.execute("SELECT phase_id, phase_key FROM dim_phase")
    mapping = {row[0]: row[1] for row in cur.fetchall()}
    cur.close()
    conn.close()
    log.info(f"Loaded dim_phase: {mapping}")
    return mapping


def load_dim_neighborhood(pg_url: str = DEFAULT_PG_URL) -> dict:
    """Load dim_neighborhood and return {name: key} mapping."""
    conn = get_pg_connection(pg_url)
    cur = conn.cursor()

    for name, terms in NEIGHBORHOOD_LEXICON.items():
        cur.execute(
            """
            INSERT INTO dim_neighborhood (neighborhood, search_terms)
            VALUES (%s, %s)
            ON CONFLICT (neighborhood) DO NOTHING
        """,
            (name, terms),
        )

    conn.commit()

    cur.execute("SELECT neighborhood, neighborhood_key FROM dim_neighborhood")
    mapping = {row[0]: row[1] for row in cur.fetchall()}
    cur.close()
    conn.close()
    log.info(f"Loaded dim_neighborhood: {mapping}")
    return mapping


def load_dim_date(pg_url: str = DEFAULT_PG_URL) -> None:
    """Populate dim_date for the analysis window (Sep 1 - Dec 31, 2025)."""
    conn = get_pg_connection(pg_url)
    cur = conn.cursor()

    raid_date = date(2025, 9, 30)
    start = date(2025, 9, 1)
    end = date(2025, 12, 31)
    current = start

    while current <= end:
        cur.execute(
            """
            INSERT INTO dim_date (date_key, day_of_week, week_number, month_name, is_weekend, days_from_raid)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (date_key) DO NOTHING
        """,
            (
                current,
                current.strftime("%A"),
                current.isocalendar()[1],
                current.strftime("%B"),
                current.weekday() >= 5,
                (current - raid_date).days,
            ),
        )
        current += timedelta(days=1)

    conn.commit()
    cur.close()
    conn.close()
    log.info("Loaded dim_date (Sep 1 - Dec 31, 2025)")


def load_fact_posts(pg_url: str = DEFAULT_PG_URL) -> int:
    """Extract from DuckDB posts_full view and load into PostgreSQL fact_posts."""
    duck = get_duckdb()

    # Check if posts_full view exists and has data
    try:
        df = duck.execute("""
            SELECT
                c.id, c.platform, c.source, c.dt_utc, c.phase, c.word_count,
                c.neighborhoods,
                e.vader_compound, e.roberta_positive, e.roberta_negative, e.roberta_neutral,
                e.sentiment_label,
                e.emo_fear, e.emo_anger, e.emo_sadness, e.emo_joy,
                e.emo_surprise, e.emo_disgust, e.emo_gratitude, e.emo_pride,
                e.dominant_emotion, e.emotion_confidence,
                t.topic_id, t.topic_label
            FROM posts_clean c
            LEFT JOIN posts_emotions e ON c.id = e.id
            LEFT JOIN posts_topics t ON c.id = t.id
            WHERE c.is_duplicate = false AND c.quality_flag = 'ok'
        """).fetchdf()
    except Exception as e:
        log.error(f"Failed to query DuckDB: {e}")
        log.info("Run the full pipeline first: make run-all")
        duck.close()
        return 0

    duck.close()

    if df.empty:
        log.warning("No data in DuckDB. Run: make run-all")
        return 0

    log.info(f"Extracted {len(df)} posts from DuckDB")

    # Get dimension mappings
    platform_map = load_dim_platform(pg_url)
    phase_map = load_dim_phase(pg_url)
    neighborhood_map = load_dim_neighborhood(pg_url)
    load_dim_date(pg_url)

    conn = get_pg_connection(pg_url)
    cur = conn.cursor()

    # Clear existing fact data for fresh load
    cur.execute("DELETE FROM bridge_post_neighborhood")
    cur.execute("DELETE FROM fact_posts")
    conn.commit()

    inserted = 0
    bridge_rows = []

    for _, row in df.iterrows():
        post_date = pd.Timestamp(row["dt_utc"]).date() if pd.notna(row["dt_utc"]) else None

        try:
            cur.execute(
                """
                INSERT INTO fact_posts (
                    post_id, platform_key, phase_key, post_date, source_name,
                    word_count, vader_compound,
                    roberta_positive, roberta_negative, roberta_neutral,
                    sentiment_label,
                    emo_fear, emo_anger, emo_sadness, emo_joy,
                    emo_surprise, emo_disgust, emo_gratitude, emo_pride,
                    dominant_emotion, emotion_confidence,
                    topic_id, topic_label
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s
                ) ON CONFLICT (post_id) DO NOTHING
            """,
                (
                    row["id"],
                    platform_map.get(row.get("platform")),
                    phase_map.get(row.get("phase")),
                    post_date,
                    row.get("source"),
                    int(row["word_count"]) if pd.notna(row.get("word_count")) else None,
                    float(row["vader_compound"]) if pd.notna(row.get("vader_compound")) else None,
                    float(row["roberta_positive"])
                    if pd.notna(row.get("roberta_positive"))
                    else None,
                    float(row["roberta_negative"])
                    if pd.notna(row.get("roberta_negative"))
                    else None,
                    float(row["roberta_neutral"]) if pd.notna(row.get("roberta_neutral")) else None,
                    row.get("sentiment_label"),
                    float(row["emo_fear"]) if pd.notna(row.get("emo_fear")) else None,
                    float(row["emo_anger"]) if pd.notna(row.get("emo_anger")) else None,
                    float(row["emo_sadness"]) if pd.notna(row.get("emo_sadness")) else None,
                    float(row["emo_joy"]) if pd.notna(row.get("emo_joy")) else None,
                    float(row["emo_surprise"]) if pd.notna(row.get("emo_surprise")) else None,
                    float(row["emo_disgust"]) if pd.notna(row.get("emo_disgust")) else None,
                    float(row["emo_gratitude"]) if pd.notna(row.get("emo_gratitude")) else None,
                    float(row["emo_pride"]) if pd.notna(row.get("emo_pride")) else None,
                    row.get("dominant_emotion"),
                    float(row["emotion_confidence"])
                    if pd.notna(row.get("emotion_confidence"))
                    else None,
                    int(row["topic_id"]) if pd.notna(row.get("topic_id")) else None,
                    row.get("topic_label"),
                ),
            )
            inserted += 1

            # Collect neighborhood bridge rows
            neighborhoods = row.get("neighborhoods")
            if neighborhoods and isinstance(neighborhoods, list):
                for n in neighborhoods:
                    nkey = neighborhood_map.get(n)
                    if nkey:
                        bridge_rows.append((row["id"], nkey))

        except Exception as e:
            log.warning(f"Skipping post {row['id']}: {e}")

    # Insert bridge table
    for post_id, nkey in bridge_rows:
        try:
            cur.execute(
                """
                INSERT INTO bridge_post_neighborhood (post_id, neighborhood_key)
                VALUES (%s, %s) ON CONFLICT DO NOTHING
            """,
                (post_id, nkey),
            )
        except Exception:
            pass

    conn.commit()
    cur.close()
    conn.close()

    log.info(f"✅ Loaded {inserted} posts into PostgreSQL fact_posts")
    log.info(f"✅ Loaded {len(bridge_rows)} neighborhood bridge rows")
    return inserted


def create_views(pg_url: str = DEFAULT_PG_URL) -> None:
    """Run the analytical views SQL file."""
    from pathlib import Path

    views_path = Path(__file__).resolve().parents[2] / "sql" / "views" / "02_analytical_views.sql"

    if not views_path.exists():
        log.warning(f"Views file not found: {views_path}")
        return

    conn = get_pg_connection(pg_url)
    cur = conn.cursor()
    cur.execute(views_path.read_text())
    conn.commit()
    cur.close()
    conn.close()
    log.info("✅ PostgreSQL analytical views created")


def run_full_load(pg_url: str = DEFAULT_PG_URL) -> None:
    """Run the complete DuckDB → PostgreSQL transfer."""
    log.info("🚀 Starting DuckDB → PostgreSQL load")
    log.info(f"Target: {pg_url}")

    create_schema(pg_url)
    count = load_fact_posts(pg_url)
    create_views(pg_url)

    log.info(f"🎉 PostgreSQL load complete: {count} posts transferred")
    log.info("Next: Connect Power BI Desktop → PostgreSQL → Build dashboard")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load DuckDB data into PostgreSQL")
    parser.add_argument(
        "--pg-url",
        default=DEFAULT_PG_URL,
        help="PostgreSQL connection URL",
    )
    args = parser.parse_args()
    run_full_load(args.pg_url)
