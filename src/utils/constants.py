"""
Shared constants for the South Shore Sentiment Study.

Updated: Extended analysis window to Dec 12, 2025 (building vacated).
Added verified event markers from Block Club Chicago reporting.
Added YouTube as third data source.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Project Root ─────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"

# ── Anchor Event ─────────────────────────────────────────────
CDT = timezone(timedelta(hours=-5))
T_ZERO = datetime(2025, 9, 30, 6, 0, 0, tzinfo=CDT)

# ── Collection Window (EXTENDED to Dec 12) ───────────────────
COLLECTION_START = datetime(2025, 9, 16, tzinfo=CDT)
COLLECTION_END = datetime(2025, 10, 14, 23, 59, 59, tzinfo=CDT)
EXTENDED_END = datetime(2025, 12, 12, 23, 59, 59, tzinfo=CDT)  # Building vacated

# ── Phase Boundaries ─────────────────────────────────────────
# Extended from 5 phases to 7 to capture tenants union + displacement
PHASES = {
    "pre": {"start": "2025-09-16", "end": "2025-09-29", "label": "Pre-Raid Baseline"},
    "event": {"start": "2025-09-29", "end": "2025-10-01", "label": "Event Window (±24h)"},
    "post_week1": {"start": "2025-10-01", "end": "2025-10-07", "label": "Post-Raid Week 1"},
    "post_week2": {"start": "2025-10-08", "end": "2025-10-14", "label": "Post-Raid Week 2"},
    "post_weeks3_5": {"start": "2025-10-15", "end": "2025-11-07", "label": "Extended Monitoring"},
    "court_action": {
        "start": "2025-11-08",
        "end": "2025-11-30",
        "label": "Court Action & Tenants Union",
    },
    "displacement": {"start": "2025-12-01", "end": "2025-12-12", "label": "Forced Displacement"},
}

# ── Target Subreddits ────────────────────────────────────────
SUBREDDITS = [
    "Chicago",
    "news",
    "Illinois",
    "AskChicago",
    "50501Chicago",
    "EyesOnIce",
    "moderatepolitics",
    "politics",
    "ICE_Raids",
    "WindyCity",
    "AskConservatives",
    "somethingiswrong2024",
    "immigration",
    "ChicagoSuburbs",
]

# ── Search Terms (expanded) ──────────────────────────────────
SEARCH_TERMS = [
    "South Shore ICE",
    "South Shore raid",
    "South Shore immigration",
    "Chicago ICE raid",
    "Operation Midway Blitz",
    "South Shore helicopters",
    "South Shore flashbang",
    "ICE raid Chicago apartment",
    "South Shore CBP",
    "Chicago immigration enforcement",
    "7500 South Shore Drive",
    "South Shore tenants union",
    "South Shore eviction",
    "Trinity Flood South Shore",
    "South Shore building cleared",
]

# ── YouTube Search Terms (video-optimized) ───────────────────
YOUTUBE_SEARCH_TERMS = [
    "South Shore ICE raid Chicago",
    "Operation Midway Blitz Chicago",
    "ICE raid Chicago apartment building",
    "South Shore Chicago helicopters flashbang",
    "Chicago ICE enforcement 2025",
    "South Shore tenants eviction Chicago",
    "7500 South Shore Drive raid",
    "Chicago sanctuary city ICE",
    "South Shore community response ICE",
    "Chicago immigration raid aftermath",
]

# ── Neighborhood Lexicon ─────────────────────────────────────
NEIGHBORHOOD_LEXICON = {
    "South Shore": [
        "South Shore",
        "south shore",
        "71st",
        "Jeffery",
        "67th",
        "79th and Exchange",
        "South Shore Drive",
        "7500 S. South Shore",
        "7500 South Shore",
    ],
    "South Chicago": [
        "South Chicago",
        "south chicago",
        "83rd",
        "Commercial Ave",
        "South Chicago Ave",
    ],
    "Woodlawn": ["Woodlawn", "woodlawn", "63rd", "Cottage Grove"],
    "Greater Grand Crossing": ["Grand Crossing", "grand crossing", "75th"],
    "Avalon Park": ["Avalon Park", "avalon park"],
    "Calumet Heights": ["Calumet Heights", "calumet heights"],
}

# ── Verified Event Markers (from Block Club Chicago reporting) ──
EVENT_MARKERS = [
    {
        "date": "2025-09-30",
        "label": "Operation Midway Blitz (t=0)",
        "color": "red",
        "verification": "L1",
        "source": "Block Club Chicago, AP, WBEZ",
    },
    {
        "date": "2025-10-01",
        "label": "Residents Return to Ransacked Apts",
        "color": "darkred",
        "verification": "L2",
        "source": "Block Club Chicago",
    },
    {
        "date": "2025-10-24",
        "label": "Distress Calls Investigation Published",
        "color": "purple",
        "verification": "L2",
        "source": "Block Club Chicago",
    },
    {
        "date": "2025-11-07",
        "label": "Judge Orders Building Cleared",
        "color": "orange",
        "verification": "L2",
        "source": "Block Club Chicago",
    },
    {
        "date": "2025-11-24",
        "label": "Tenants Union Formed",
        "color": "blue",
        "verification": "L2",
        "source": "Block Club Chicago",
    },
    {
        "date": "2025-12-08",
        "label": "Eviction Deadline Denied Extension",
        "color": "brown",
        "verification": "L2",
        "source": "Block Club Chicago",
    },
    {
        "date": "2025-12-12",
        "label": "Building Vacated",
        "color": "black",
        "verification": "L2",
        "source": "Block Club Chicago",
    },
]

# ── GoEmotions → Target Emotion Mapping ──────────────────────
GOEMOTIONS_MAP = {
    "admiration": "pride",
    "amusement": "joy",
    "anger": "anger",
    "annoyance": "anger",
    "approval": "gratitude",
    "caring": "gratitude",
    "confusion": "fear",
    "curiosity": "surprise",
    "desire": "joy",
    "disappointment": "sadness",
    "disapproval": "anger",
    "disgust": "disgust",
    "embarrassment": "sadness",
    "excitement": "joy",
    "fear": "fear",
    "gratitude": "gratitude",
    "grief": "sadness",
    "joy": "joy",
    "love": "gratitude",
    "nervousness": "fear",
    "optimism": "joy",
    "pride": "pride",
    "realization": "surprise",
    "relief": "joy",
    "remorse": "sadness",
    "sadness": "sadness",
    "surprise": "surprise",
}

TARGET_EMOTIONS = ["fear", "anger", "sadness", "joy", "surprise", "disgust", "gratitude", "pride"]

# ── Platforms ────────────────────────────────────────────────
PLATFORMS = ["reddit", "news_comment", "youtube"]

# ── Platform Display Colors ──────────────────────────────────
PLATFORM_COLORS = {
    "reddit": "#FF4500",
    "news_comment": "#1DA1F2",
    "youtube": "#FF0000",
}

# ── DB Tables ────────────────────────────────────────────────
TABLE_POSTS_RAW = "posts_raw"
TABLE_POSTS_CLEAN = "posts_clean"
TABLE_EMOTIONS = "posts_emotions"
TABLE_TOPICS = "posts_topics"
