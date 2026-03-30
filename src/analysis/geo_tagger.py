"""Neighborhood geo-tagging. Already handled in cleaning.py — this is for standalone runs."""

from src.utils.constants import NEIGHBORHOOD_LEXICON
from src.utils.db import get_connection
from src.utils.logger import log


def run_geo_tagging():
    """Re-run geo tagging on posts_clean (updates neighborhoods column)."""
    log.info("Running geo-tagging pass")
    conn = get_connection()
    df = conn.execute("SELECT id, text_clean FROM posts_clean WHERE quality_flag='ok'").fetchdf()
    if df.empty:
        conn.close()
        return

    for _, row in df.iterrows():
        text_lower = (row["text_clean"] or "").lower()
        detected = []
        for neighborhood, terms in NEIGHBORHOOD_LEXICON.items():
            if any(t.lower() in text_lower for t in terms):
                detected.append(neighborhood)
        if detected:
            conn.execute(
                "UPDATE posts_clean SET neighborhoods=?, has_geo=true WHERE id=?",
                [list(set(detected)), row["id"]],
            )

    count = conn.execute("SELECT COUNT(*) FROM posts_clean WHERE has_geo=true").fetchone()[0]
    log.info(f"Geo-tagged {count} posts with neighborhood mentions")
    conn.close()


if __name__ == "__main__":
    run_geo_tagging()
