"""
Platform Comparison Charts — Reddit vs YouTube vs News.

Generates side-by-side visualizations comparing sentiment, emotions,
engagement, and response patterns across the three data sources.

Used by: Streamlit dashboard (tab), Power BI (exported images), report.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.utils.constants import PHASES, TARGET_EMOTIONS
from src.utils.logger import log

PLATFORM_COLORS = {
    "reddit": "#FF4500",
    "youtube": "#FF0000",
    "news_comment": "#1DA1F2",
}

PLATFORM_LABELS = {
    "reddit": "Reddit",
    "youtube": "YouTube",
    "news_comment": "News",
}

DARK_BG = "#0E1117"
CARD_BG = "#1a1a2e"
GRID_COLOR = "#2a2a3e"
TEXT_COLOR = "#e0e0e0"


def _apply_dark_layout(fig: go.Figure, title: str = "") -> go.Figure:
    """Apply consistent dark theme to a plotly figure."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=TEXT_COLOR)),
        paper_bgcolor=DARK_BG,
        plot_bgcolor=CARD_BG,
        font=dict(color=TEXT_COLOR, size=11),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        margin=dict(l=60, r=30, t=60, b=50),
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    fig.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    return fig


def platform_sentiment_bars(df: pd.DataFrame) -> go.Figure:
    """Clustered bar chart: average sentiment by platform and phase."""
    if df.empty:
        return go.Figure()

    grouped = df.groupby(["phase", "platform"])["vader_compound"].mean().reset_index()

    phase_order = list(PHASES.keys())
    phase_labels = {k: v["label"] for k, v in PHASES.items()}

    fig = go.Figure()
    for platform, color in PLATFORM_COLORS.items():
        pdata = grouped[grouped["platform"] == platform]
        if pdata.empty:
            continue
        # Sort by phase order
        pdata = pdata.copy()
        pdata["order"] = pdata["phase"].map({p: i for i, p in enumerate(phase_order)})
        pdata = pdata.sort_values("order")

        fig.add_trace(
            go.Bar(
                name=PLATFORM_LABELS.get(platform, platform),
                x=[phase_labels.get(p, p) for p in pdata["phase"]],
                y=pdata["vader_compound"],
                marker_color=color,
                opacity=0.85,
            )
        )

    fig.update_layout(barmode="group")
    return _apply_dark_layout(fig, "Sentiment by Platform × Phase")


def emotion_radar(df: pd.DataFrame) -> go.Figure:
    """Radar chart comparing emotion profiles across platforms."""
    if df.empty:
        return go.Figure()

    emotions = TARGET_EMOTIONS
    emo_cols = [f"emo_{e}" for e in emotions]

    fig = go.Figure()
    for platform, color in PLATFORM_COLORS.items():
        pdata = df[df["platform"] == platform]
        if pdata.empty:
            continue

        values = [pdata[col].mean() if col in pdata.columns else 0 for col in emo_cols]
        # Close the polygon
        values_closed = values + [values[0]]
        labels_closed = emotions + [emotions[0]]

        fig.add_trace(
            go.Scatterpolar(
                r=values_closed,
                theta=labels_closed,
                name=PLATFORM_LABELS.get(platform, platform),
                fill="toself",
                fillcolor=f"{color}20",
                line=dict(color=color, width=2),
            )
        )

    fig.update_layout(
        polar=dict(
            bgcolor=CARD_BG,
            radialaxis=dict(visible=True, gridcolor=GRID_COLOR, color=TEXT_COLOR),
            angularaxis=dict(gridcolor=GRID_COLOR, color=TEXT_COLOR),
        ),
    )
    return _apply_dark_layout(fig, "Emotion Profiles: Reddit vs YouTube vs News")


def sentiment_distribution(df: pd.DataFrame) -> go.Figure:
    """Violin plot showing sentiment distribution per platform."""
    if df.empty or "vader_compound" not in df.columns:
        return go.Figure()

    fig = go.Figure()
    for platform, color in PLATFORM_COLORS.items():
        pdata = df[df["platform"] == platform]
        if pdata.empty:
            continue

        fig.add_trace(
            go.Violin(
                y=pdata["vader_compound"],
                name=PLATFORM_LABELS.get(platform, platform),
                box_visible=True,
                meanline_visible=True,
                line_color=color,
                fillcolor=f"{color}30",
                opacity=0.8,
            )
        )

    fig.update_layout(showlegend=True, violinmode="group")
    return _apply_dark_layout(fig, "Sentiment Distribution by Platform")


def platform_timeline(df: pd.DataFrame) -> go.Figure:
    """Line chart: daily sentiment per platform over time."""
    if df.empty or "dt_utc" not in df.columns:
        return go.Figure()

    df = df.copy()
    df["date"] = pd.to_datetime(df["dt_utc"]).dt.date

    fig = go.Figure()
    for platform, color in PLATFORM_COLORS.items():
        pdata = df[df["platform"] == platform]
        if pdata.empty:
            continue

        daily = pdata.groupby("date")["vader_compound"].mean().reset_index()
        daily = daily.sort_values("date")

        # 3-day rolling average for smoothness
        daily["rolling"] = daily["vader_compound"].rolling(3, min_periods=1).mean()

        fig.add_trace(
            go.Scatter(
                x=daily["date"],
                y=daily["rolling"],
                name=PLATFORM_LABELS.get(platform, platform),
                line=dict(color=color, width=2.5),
                mode="lines",
            )
        )

    return _apply_dark_layout(fig, "Sentiment Trajectory by Platform (3-day rolling avg)")


def engagement_vs_sentiment(df: pd.DataFrame) -> go.Figure:
    """Scatter plot: engagement (likes) vs sentiment, colored by platform."""
    if df.empty:
        return go.Figure()

    fig = go.Figure()
    for platform, color in PLATFORM_COLORS.items():
        pdata = df[df["platform"] == platform]
        if pdata.empty:
            continue

        # Sample for performance if too many points
        if len(pdata) > 500:
            pdata = pdata.sample(500, random_state=42)

        fig.add_trace(
            go.Scatter(
                x=pdata.get("vader_compound", []),
                y=pdata.get("like_count", pdata.get("score", [])),
                name=PLATFORM_LABELS.get(platform, platform),
                mode="markers",
                marker=dict(
                    color=color,
                    size=6,
                    opacity=0.5,
                ),
            )
        )

    fig.update_xaxes(title="Sentiment Score")
    fig.update_yaxes(title="Engagement (Likes/Score)")
    return _apply_dark_layout(fig, "Engagement vs Sentiment by Platform")


def platform_volume_stacked(df: pd.DataFrame) -> go.Figure:
    """Stacked area chart: post volume by platform over time."""
    if df.empty or "dt_utc" not in df.columns:
        return go.Figure()

    df = df.copy()
    df["date"] = pd.to_datetime(df["dt_utc"]).dt.date

    fig = go.Figure()
    for platform, color in PLATFORM_COLORS.items():
        pdata = df[df["platform"] == platform]
        if pdata.empty:
            continue

        daily = pdata.groupby("date").size().reset_index(name="count")
        daily = daily.sort_values("date")

        fig.add_trace(
            go.Scatter(
                x=daily["date"],
                y=daily["count"],
                name=PLATFORM_LABELS.get(platform, platform),
                stackgroup="one",
                line=dict(color=color),
                fillcolor=f"{color}40",
            )
        )

    return _apply_dark_layout(fig, "Post Volume by Platform Over Time")


def platform_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    """Generate a summary DataFrame comparing platforms."""
    if df.empty:
        return pd.DataFrame()

    rows = []
    for platform in PLATFORM_COLORS:
        pdata = df[df["platform"] == platform]
        if pdata.empty:
            continue

        row = {
            "Platform": PLATFORM_LABELS.get(platform, platform),
            "Total Posts": len(pdata),
            "Avg Sentiment": round(pdata["vader_compound"].mean(), 3)
            if "vader_compound" in pdata
            else None,
            "% Negative": round((pdata["sentiment_label"] == "negative").mean() * 100, 1)
            if "sentiment_label" in pdata
            else None,
            "% Positive": round((pdata["sentiment_label"] == "positive").mean() * 100, 1)
            if "sentiment_label" in pdata
            else None,
            "Dominant Emotion": pdata["dominant_emotion"].mode().iloc[0]
            if "dominant_emotion" in pdata and not pdata["dominant_emotion"].mode().empty
            else None,
            "Avg Fear": round(pdata["emo_fear"].mean(), 3) if "emo_fear" in pdata else None,
            "Avg Anger": round(pdata["emo_anger"].mean(), 3) if "emo_anger" in pdata else None,
            "Avg Gratitude": round(pdata["emo_gratitude"].mean(), 3)
            if "emo_gratitude" in pdata
            else None,
        }
        rows.append(row)

    return pd.DataFrame(rows)


def render_all_charts(df: pd.DataFrame) -> dict[str, go.Figure]:
    """Generate all platform comparison charts. Returns {name: figure}."""
    log.info(f"Generating platform comparison charts for {len(df)} posts")
    return {
        "sentiment_bars": platform_sentiment_bars(df),
        "emotion_radar": emotion_radar(df),
        "sentiment_distribution": sentiment_distribution(df),
        "timeline": platform_timeline(df),
        "engagement_scatter": engagement_vs_sentiment(df),
        "volume_stacked": platform_volume_stacked(df),
    }
