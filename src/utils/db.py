"""
DuckDB connection manager and schema initialization.
"""

import os
from pathlib import Path

import duckdb

from src.utils.constants import PROJECT_ROOT
from src.utils.logger import log

DB_PATH = PROJECT_ROOT / "data" / "sentiment_study.duckdb"

# Detect Streamlit Cloud (read-only filesystem)
IS_STREAMLIT_CLOUD = (
    os.path.exists("/mount/src") or os.environ.get("STREAMLIT_SERVER_HEADLESS") == "true"
)

# Expected columns for posts_clean (for migration when table exists with older schema)
POSTS_CLEAN_COLUMNS = [
    ("id", "VARCHAR PRIMARY KEY"),
    ("platform", "VARCHAR"),
    ("source", "VARCHAR"),
    ("dt_utc", "TIMESTAMP WITH TIME ZONE"),
    ("text_original", "VARCHAR"),
    ("text_clean", "VARCHAR"),
    ("text_tokens", "VARCHAR[]"),
    ("text_lemmas", "VARCHAR[]"),
    ("word_count", "INTEGER"),
    ("phase", "VARCHAR"),
    ("neighborhoods", "VARCHAR[]"),
    ("has_geo", "BOOLEAN DEFAULT false"),
    ("is_duplicate", "BOOLEAN DEFAULT false"),
    ("quality_flag", "VARCHAR DEFAULT 'ok'"),
]


def _ensure_posts_clean_columns(conn: duckdb.DuckDBPyConnection) -> None:
    """Add missing columns to posts_clean for DBs created with an older schema."""
    try:
        existing = set(
            row[0]
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'posts_clean'"
            ).fetchall()
        )
    except Exception:
        return
    for col_name, col_def in POSTS_CLEAN_COLUMNS:
        if col_name in existing:
            continue
        try:
            # PRIMARY KEY only on initial CREATE; use plain type when adding
            spec = col_def.replace(" PRIMARY KEY", "") if "PRIMARY KEY" in col_def else col_def
            conn.execute(f"ALTER TABLE posts_clean ADD COLUMN {col_name} {spec}")
        except Exception:
            pass


def get_connection(db_path: Path | str | None = None) -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection. Opens read-only on Streamlit Cloud."""
    path = Path(db_path) if db_path else DB_PATH

    if IS_STREAMLIT_CLOUD:
        # Streamlit Cloud has a read-only filesystem; skip mkdir, open read-only
        conn = duckdb.connect(str(path), read_only=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = duckdb.connect(str(path))
    return conn


def init_database(db_path: Path | str | None = None) -> None:
    """Initialize database with all required tables."""
    if IS_STREAMLIT_CLOUD:
        log.info("☁️ Streamlit Cloud detected — skipping DB init (read-only)")
        return

    conn = get_connection(db_path)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts_raw (
            id              VARCHAR PRIMARY KEY,
            platform        VARCHAR NOT NULL,         -- 'reddit' | 'news_comment'
            source          VARCHAR,                  -- subreddit name or news domain
            url             VARCHAR,
            dt_utc          TIMESTAMP WITH TIME ZONE,
            text            VARCHAR,
            title           VARCHAR,                  -- for Reddit submissions
            author_display  VARCHAR,
            score           INTEGER DEFAULT 0,
            like_count      INTEGER DEFAULT 0,
            reply_count     INTEGER DEFAULT 0,
            share_count     INTEGER DEFAULT 0,
            parent_id       VARCHAR,                  -- for comments/replies
            post_type       VARCHAR,                  -- 'submission' | 'comment'
            detected_locs   VARCHAR[],                -- neighborhood mentions
            anchors         VARCHAR,                  -- 'pre' | 'event' | 'post_week1' etc.
            search_term     VARCHAR,                  -- query that found this post
            collected_at    TIMESTAMP DEFAULT now()
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts_clean (
            id              VARCHAR PRIMARY KEY,
            platform        VARCHAR,
            source          VARCHAR,
            dt_utc          TIMESTAMP WITH TIME ZONE,
            text_original   VARCHAR,
            text_clean      VARCHAR,                  -- normalized text
            text_tokens     VARCHAR[],                -- tokenized
            text_lemmas     VARCHAR[],                -- lemmatized
            word_count      INTEGER,
            phase           VARCHAR,                  -- temporal phase
            neighborhoods   VARCHAR[],                -- detected neighborhood tags
            has_geo         BOOLEAN DEFAULT false,
            is_duplicate    BOOLEAN DEFAULT false,
            quality_flag    VARCHAR DEFAULT 'ok'      -- 'ok' | 'short' | 'spam' | 'non_english'
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts_emotions (
            id                  VARCHAR PRIMARY KEY,
            -- VADER scores
            vader_compound      FLOAT,
            vader_positive      FLOAT,
            vader_negative      FLOAT,
            vader_neutral       FLOAT,
            -- RoBERTa sentiment
            roberta_positive    FLOAT,
            roberta_negative    FLOAT,
            roberta_neutral     FLOAT,
            -- GoEmotions (target 8)
            emo_fear            FLOAT,
            emo_anger           FLOAT,
            emo_sadness         FLOAT,
            emo_joy             FLOAT,
            emo_surprise        FLOAT,
            emo_disgust         FLOAT,
            emo_gratitude       FLOAT,
            emo_pride           FLOAT,
            -- Derived
            dominant_emotion    VARCHAR,
            emotion_confidence  FLOAT,
            sentiment_label     VARCHAR                -- 'positive' | 'negative' | 'neutral'
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts_topics (
            id              VARCHAR PRIMARY KEY,
            topic_id        INTEGER,
            topic_label     VARCHAR,
            topic_prob      FLOAT,
            top_terms       VARCHAR[]
        );
    """)

    # Migrate posts_clean if it was created with an older schema (missing is_duplicate, quality_flag, etc.)
    _ensure_posts_clean_columns(conn)

    # Convenience view joining all tables
    conn.execute("""
        CREATE OR REPLACE VIEW posts_full AS
        SELECT
            c.*,
            e.vader_compound, e.vader_positive, e.vader_negative, e.vader_neutral,
            e.roberta_positive, e.roberta_negative, e.roberta_neutral,
            e.emo_fear, e.emo_anger, e.emo_sadness, e.emo_joy,
            e.emo_surprise, e.emo_disgust, e.emo_gratitude, e.emo_pride,
            e.dominant_emotion, e.emotion_confidence, e.sentiment_label,
            t.topic_id, t.topic_label, t.topic_prob, t.top_terms
        FROM posts_clean c
        LEFT JOIN posts_emotions e ON c.id = e.id
        LEFT JOIN posts_topics t ON c.id = t.id
        WHERE c.is_duplicate = false
          AND c.quality_flag = 'ok';
    """)

    conn.close()
    log.info(f"✅ Database initialized at {db_path or DB_PATH}")


def query_df(sql: str, db_path: Path | str | None = None):
    """Execute SQL and return a Pandas DataFrame."""
    conn = get_connection(db_path)
    try:
        return conn.execute(sql).fetchdf()
    finally:
        conn.close()


def execute(sql: str, params=None, db_path: Path | str | None = None):
    """Execute SQL statement."""
    if IS_STREAMLIT_CLOUD:
        log.warning("☁️ Write operation skipped on Streamlit Cloud (read-only)")
        return

    conn = get_connection(db_path)
    try:
        if params:
            conn.execute(sql, params)
        else:
            conn.execute(sql)
    finally:
        conn.close()


if __name__ == "__main__":
    init_database()
