"""Shared Plotly styling constants and helpers for all visualization modules."""

import plotly.graph_objects as go

DARK_BG = "#0e1117"
DARK_BORDER = "#333333"
TEXT_COLOR = "#FAFAFA"

EMOTION_COLORS = {
    "fear": "#FF4444",
    "anger": "#FF8C00",
    "sadness": "#4A90D9",
    "joy": "#FFE135",
    "surprise": "#9B59B6",
    "disgust": "#1ABC9C",
    "gratitude": "#00E676",
    "pride": "#FF69B4",
}

KEY_EMOTIONS = ["fear", "anger", "joy", "gratitude", "sadness", "pride"]


def apply_dark_layout(fig: go.Figure) -> go.Figure:
    """Single source of truth for hover + background styling."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_BG,
        font=dict(color=TEXT_COLOR),
        hoverlabel=dict(
            bgcolor="rgba(14,17,23,1)",
            font=dict(color=TEXT_COLOR, size=12),
            bordercolor=DARK_BORDER,
        ),
        legend=dict(bgcolor=DARK_BG),
    )
    return fig
