"""
Text Cleaning Pipeline — Normalization, deduplication, quality flagging, and phase tagging.

Updated: Extended phase detection to 7 phases (through Dec 12, 2025).
Fixed: Schema alignment with init_database(), proper is_duplicate/quality_flag columns.
"""

import hashlib
import re
from datetime import datetime

import pandas as pd

from src.utils.constants import (
    NEIGHBORHOOD_LEXICON,
    PHASES,
    TABLE_POSTS_CLEAN,
    TABLE_POSTS_RAW,
)
from src.utils.db import get_connection, init_database
from src.utils.logger import log

# ── Text Cleaning ────────────────────────────────────────────


def clean_text(text: str) -> str:
    """Normalize a post's text for NLP processing."""
    if not isinstance(text, str):
        return ""

    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"www\.\S+", "", text)
    # Remove Reddit-specific markdown
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)  # [text](url) → text
    text = re.sub(r"/?r/\w+", "", text)  # r/subreddit
    text = re.sub(r"/?u/\w+", "", text)  # u/username
    # Strip @mentions
    text = re.sub(r"@\w+", "", text)
    # Strip [deleted] / [removed]
    text = re.sub(r"\[(deleted|removed)\]", "", text)
    # Convert #hashtags to words
    text = re.sub(r"#(\w+)", r"\1", text)
    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Remove very short results
    if len(text) < 10:
        return ""

    return text


def detect_phase(dt_str: str) -> str:
    """Assign temporal phase based on datetime string.

    Supports 7 phases:
      pre, event, post_week1, post_week2, post_weeks3_5,
      court_action, displacement
    """
    try:
        if isinstance(dt_str, datetime):
            dt = dt_str
        else:
            dt = pd.to_datetime(dt_str, utc=True)

        date_str = dt.strftime("%Y-%m-%d")

        for phase_name, phase_info in PHASES.items():
            if phase_info["start"] <= date_str <= phase_info["end"]:
                return phase_name

        return "outside_window"
    except Exception:
        return "unknown"


def detect_neighborhoods(text: str) -> list[str]:
    """Detect neighborhood mentions from text using lexicon matching."""
    if not text:
        return []
    text_lower = text.lower()
    detected = []
    for neighborhood, terms in NEIGHBORHOOD_LEXICON.items():
        if any(t.lower() in text_lower for t in terms):
            detected.append(neighborhood)
    return list(set(detected))


def compute_text_hash(text: str) -> str:
    """SHA-256 hash for deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def flag_quality(text: str, word_count: int) -> str:
    """Flag post quality: 'ok', 'short', 'spam', or 'non_english'."""
    if word_count < 3:
        return "short"
    # Simple spam detection: excessive URLs or repetitive patterns
    url_count = len(re.findall(r"https?://", text))
    if url_count >= 4:
        return "spam"
    # Very repetitive text
    words = text.lower().split()
    if len(words) > 5:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.3:
            return "spam"
    return "ok"


# ── Main Pipeline ────────────────────────────────────────────


def run_cleaning():
    """Execute the full cleaning pipeline."""
    init_database()
    con = get_connection()

    # Load raw posts
    try:
        df = con.execute(f"SELECT * FROM {TABLE_POSTS_RAW}").fetchdf()
    except Exception:
        log.error(f"Table {TABLE_POSTS_RAW} does not exist. Run ingestion first.")
        con.close()
        return

    log.info(f"Loaded {len(df)} raw posts")

    if df.empty:
        log.warning("No raw posts to clean")
        con.close()
        return

    # Clean text
    df["text_clean"] = df["text"].apply(clean_text)
    df = df[df["text_clean"].str.len() > 0].copy()
    log.info(f"After text cleaning: {len(df)} posts")

    # Text hash for deduplication
    df["text_hash"] = df["text_clean"].apply(compute_text_hash)

    # Mark duplicates (keep first, flag rest)
    df["is_duplicate"] = df.duplicated(subset=["text_hash"], keep="first")
    n_dupes = df["is_duplicate"].sum()
    log.info(f"Flagged {n_dupes} duplicate posts")

    # Phase tagging
    df["phase"] = df["dt_utc"].astype(str).apply(detect_phase)

    # Filter out posts outside analysis window
    valid_phases = list(PHASES.keys())
    df = df[df["phase"].isin(valid_phases)].copy()
    log.info(f"After date filtering: {len(df)} posts within analysis window")

    # Log phase distribution
    phase_dist = df["phase"].value_counts().to_dict()
    log.info(f"Phase distribution: {phase_dist}")

    # Word count
    df["word_count"] = df["text_clean"].str.split().str.len()

    # Quality flagging
    df["quality_flag"] = df.apply(
        lambda row: flag_quality(row["text_clean"], row["word_count"]), axis=1
    )
    quality_dist = df["quality_flag"].value_counts().to_dict()
    log.info(f"Quality distribution: {quality_dist}")

    # Geo-tagging (neighborhood detection)
    df["neighborhoods"] = df["text_clean"].apply(detect_neighborhoods)
    df["has_geo"] = df["neighborhoods"].apply(lambda x: len(x) > 0)
    geo_count = df["has_geo"].sum()
    log.info(f"Geo-tagged {geo_count} posts with neighborhood mentions")

    # Build posts_clean table matching init_database() schema
    con.execute(f"DROP TABLE IF EXISTS {TABLE_POSTS_CLEAN}")
    con.register("df_clean", df)
    con.execute(f"""
        CREATE TABLE {TABLE_POSTS_CLEAN} AS
        SELECT
            id,
            platform,
            source,
            dt_utc,
            text AS text_original,
            text_clean,
            NULL::VARCHAR[] AS text_tokens,
            NULL::VARCHAR[] AS text_lemmas,
            word_count,
            phase,
            neighborhoods,
            has_geo,
            is_duplicate,
            quality_flag
        FROM df_clean
    """)

    count = con.execute(f"SELECT COUNT(*) FROM {TABLE_POSTS_CLEAN}").fetchone()[0]
    usable = con.execute(
        f"SELECT COUNT(*) FROM {TABLE_POSTS_CLEAN} "
        f"WHERE is_duplicate = false AND quality_flag = 'ok'"
    ).fetchone()[0]
    log.info(f"Stored {count} clean posts ({usable} usable) to {TABLE_POSTS_CLEAN}")

    # Platform breakdown
    plat_df = con.execute(
        f"SELECT platform, COUNT(*) as n FROM {TABLE_POSTS_CLEAN} "
        f"WHERE is_duplicate = false AND quality_flag = 'ok' GROUP BY platform"
    ).fetchdf()
    log.info(f"Platform breakdown (usable):\n{plat_df.to_string(index=False)}")

    con.close()


if __name__ == "__main__":
    run_cleaning()
