"""Neighborhood-level geographic visualizations."""

import pandas as pd
import plotly.graph_objects as go

from src.visualization.chart_style import EMOTION_COLORS, TEXT_COLOR, apply_dark_layout


def create_neighborhood_chart(geo_df: pd.DataFrame) -> go.Figure:
    if geo_df.empty:
        fig = go.Figure()
        fig.update_layout(title="No geo-tagged data available")
        return apply_dark_layout(fig)

    fig = go.Figure()
    key_emos = ["fear", "anger", "joy", "gratitude"]

    for emo in key_emos:
        col = f"{emo}_mean"
        if col in geo_df.columns:
            fig.add_trace(
                go.Bar(
                    name=emo.capitalize(),
                    x=geo_df["neighborhood"],
                    y=geo_df[col],
                    marker_color=EMOTION_COLORS.get(emo, "gray"),
                )
            )

    fig.update_layout(
        title="Emotion Intensity by Neighborhood",
        barmode="group",
        height=450,
        yaxis_title="Mean Emotion Score",
        annotations=[
            dict(
                text="⚠️ Geo-inference from text mentions; not GPS coordinates",
                xref="paper",
                yref="paper",
                x=0.5,
                y=-0.15,
                showarrow=False,
                font=dict(size=10, color=TEXT_COLOR),
            )
        ],
    )

    return apply_dark_layout(fig)


def create_geo_fear_timeline(df: pd.DataFrame) -> go.Figure:
    """Share of high-fear posts by neighborhood over phases."""
    if df.empty or "neighborhoods" not in df.columns:
        return apply_dark_layout(go.Figure())

    geo_df = df[df.get("has_geo", False)].copy()
    if geo_df.empty:
        return apply_dark_layout(go.Figure())

    geo_df = geo_df.explode("neighborhoods")
    if "emo_fear" not in geo_df.columns:
        return apply_dark_layout(go.Figure())

    geo_df["high_fear"] = geo_df["emo_fear"] > 0.3

    ct = pd.crosstab(
        geo_df["phase"],
        geo_df["neighborhoods"],
        values=geo_df["high_fear"],
        aggfunc="mean",
    ).fillna(0)

    fig = go.Figure()
    for col in ct.columns:
        fig.add_trace(go.Scatter(x=ct.index, y=ct[col], mode="lines+markers", name=str(col)))

    fig.update_layout(
        title="Share of High-Fear Posts by Neighborhood & Phase",
        height=400,
        yaxis_title="Share (>0.3 fear)",
    )

    return apply_dark_layout(fig)
