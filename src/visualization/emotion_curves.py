"""Plotly emotion trajectory charts with event overlays and robust hover styling."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.utils.constants import EVENT_MARKERS, PHASES, TARGET_EMOTIONS
from src.visualization.chart_style import EMOTION_COLORS, KEY_EMOTIONS, apply_dark_layout


def create_emotion_trajectory_chart(
    daily_df: pd.DataFrame,
    title: str = "Emotion Trajectories Over Time",
    selected_emotions: list[str] | None = None,
) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.75, 0.25],
        subplot_titles=("Emotion Intensity", "Post Volume"),
    )

    display_emotions = selected_emotions if selected_emotions else KEY_EMOTIONS
    for emo in display_emotions:
        col = f"{emo}_mean"
        if col in daily_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=daily_df["date"],
                    y=daily_df[col],
                    name=emo.capitalize(),
                    line=dict(color=EMOTION_COLORS[emo], width=2.5),
                    mode="lines+markers",
                    marker=dict(size=4),
                ),
                row=1,
                col=1,
            )

    if "n_posts" in daily_df.columns:
        fig.add_trace(
            go.Bar(
                x=daily_df["date"],
                y=daily_df["n_posts"],
                name="Posts",
                marker_color="rgba(160,160,160,0.35)",
            ),
            row=2,
            col=1,
        )

    for m in EVENT_MARKERS:
        fig.add_shape(
            type="line",
            x0=m["date"],
            x1=m["date"],
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color=m["color"], width=1.5, dash="dash"),
        )
        fig.add_annotation(
            x=m["date"],
            y=1.03,
            yref="paper",
            text=m["label"],
            showarrow=False,
            font=dict(size=9, color=m["color"]),
            textangle=-30,
        )

    fig.update_layout(
        title=title,
        height=650,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    fig.update_yaxes(title_text="Mean Probability", row=1, col=1)
    fig.update_yaxes(title_text="# Posts", row=2, col=1)

    return apply_dark_layout(fig)


def create_phase_comparison_chart(phase_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if phase_df.empty:
        fig.update_layout(title="Emotion by Phase (95% CI)")
        return apply_dark_layout(fig)

    order = [p for p in PHASES if p in phase_df["phase"].values]
    labels = [PHASES[p]["label"] for p in order]

    for emo in KEY_EMOTIONS:
        col = f"{emo}_mean"
        if col not in phase_df.columns:
            continue

        vals, errs = [], []
        for p in order:
            r = phase_df[phase_df["phase"] == p]
            if not r.empty:
                mean = r[col].iloc[0]
                ci_hi = r.get(f"{emo}_ci_hi", pd.Series([mean])).iloc[0]
                vals.append(mean)
                errs.append(max(ci_hi - mean, 0))

        if vals:
            fig.add_trace(
                go.Bar(
                    name=emo.capitalize(),
                    x=labels[: len(vals)],
                    y=vals,
                    error_y=dict(type="data", array=errs, visible=True),
                    marker_color=EMOTION_COLORS[emo],
                )
            )

    fig.update_layout(title="Emotion by Phase (95% CI)", barmode="group", height=500)
    return apply_dark_layout(fig)


def create_platform_contrast_chart(platform_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if platform_df.empty:
        fig.update_layout(title="Platform Emotion Profiles")
        return apply_dark_layout(fig)

    emos = KEY_EMOTIONS
    for _, row in platform_df.iterrows():
        vals = [row.get(f"{e}_mean", 0) for e in emos] + [row.get(f"{emos[0]}_mean", 0)]
        fig.add_trace(
            go.Scatterpolar(
                r=vals,
                theta=[e.capitalize() for e in emos] + [emos[0].capitalize()],
                name=str(row.get("platform", "Unknown")),
                fill="toself",
                opacity=0.6,
            )
        )

    fig.update_layout(
        title="Platform Emotion Profiles",
        polar=dict(radialaxis=dict(visible=True, range=[0, 0.5])),
        height=500,
    )
    return apply_dark_layout(fig)


def create_sentiment_heatmap(daily_df: pd.DataFrame) -> go.Figure:
    cols = [f"{e}_mean" for e in TARGET_EMOTIONS if f"{e}_mean" in daily_df.columns]
    labels = [c.replace("_mean", "").capitalize() for c in cols]

    fig = go.Figure(
        data=go.Heatmap(
            z=daily_df[cols].values.T if cols else [],
            x=daily_df["date"] if "date" in daily_df.columns else [],
            y=labels,
            colorscale="RdYlGn_r",
            colorbar=dict(title="Intensity"),
        )
    )

    for m in EVENT_MARKERS:
        fig.add_shape(
            type="line",
            x0=m["date"],
            x1=m["date"],
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color=m["color"], width=1, dash="dash"),
        )

    fig.update_layout(title="Emotion Heatmap", height=420)
    return apply_dark_layout(fig)
