"""
Plotly Chart Builders
----------------------
All charts return go.Figure objects for use with st.plotly_chart().
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ui.theme import get_theme, get_plotly_template


def _chart_colors() -> dict[str, str]:
    """
    Pull the palette used by chart builders from the active theme.
    Called at chart-build time so every render reflects the current mode.
    """
    t = get_theme()
    return {
        "buy":          t["success"],
        "sell":         t["danger"],
        "strategy":     t["link"],
        "benchmark":    t["text_muted"],
        "candle_up":    t["candle_up"],
        "candle_down":  t["candle_down"],
        "sma_short":    t["orange"],
        "sma_long":     t["purple"],
        "rsi":          t["cyan"],
        "drawdown":     t["danger"],
        "volume_up":    t["volume_up"],
        "volume_down":  t["volume_down"],
        "bg":           t["bg"],
        "grid":         t["grid"],
    }


def candlestick_with_signals(
    df: pd.DataFrame,
    trade_log: pd.DataFrame,
    strategy_name: str = "",
) -> go.Figure:
    """
    Interactive candlestick chart with:
      - Buy markers (green triangle-up) on entry dates
      - Sell markers (red triangle-down) on exit dates
      - SMA lines overlay (if SMA_short / SMA_long columns exist)
      - RSI subplot (if RSI column exists)

    Parameters
    ----------
    df            : DataFrame with OHLCV + optional SMA_short, SMA_long, RSI columns
    trade_log     : DataFrame with entry_date / exit_date columns
    strategy_name : str — used in chart title
    """
    c = _chart_colors()
    template = get_plotly_template()

    has_rsi = "RSI" in df.columns
    has_sma = "SMA_short" in df.columns and "SMA_long" in df.columns
    has_volume = "Volume" in df.columns and df["Volume"].sum() > 0

    # Build row layout: price (always) + optional volume + optional RSI
    titles = [f"{strategy_name} — Price Chart"]
    heights = [1.0]
    if has_volume:
        titles.append("Volume")
        heights.append(0.18)
    if has_rsi:
        titles.append("RSI")
        heights.append(0.28)
    # Normalize so heights sum to 1
    total = sum(heights)
    heights = [h / total for h in heights]

    rows = len(heights)
    volume_row = 2 if has_volume else None
    rsi_row = (3 if has_volume else 2) if has_rsi else None

    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=heights,
        subplot_titles=tuple(titles),
    )

    # --- Candlestick ---
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
            increasing_line_color=c["candle_up"],
            decreasing_line_color=c["candle_down"],
            increasing_fillcolor=c["candle_up"],
            decreasing_fillcolor=c["candle_down"],
        ),
        row=1, col=1,
    )

    # --- SMA overlays ---
    if has_sma:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["SMA_short"],
                mode="lines", name="SMA Short",
                line=dict(color=c["sma_short"], width=1.5),
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["SMA_long"],
                mode="lines", name="SMA Long",
                line=dict(color=c["sma_long"], width=1.5),
            ),
            row=1, col=1,
        )

    # --- Buy markers ---
    if not trade_log.empty and "entry_date" in trade_log.columns:
        entry_dates = pd.to_datetime(trade_log["entry_date"])
        entry_prices = df.loc[df.index.isin(entry_dates), "Low"] * 0.985
        fig.add_trace(
            go.Scatter(
                x=entry_dates,
                y=entry_prices.values,
                mode="markers",
                name="Buy",
                marker=dict(
                    symbol="triangle-up",
                    color=c["buy"],
                    size=12,
                    line=dict(color="white", width=1),
                ),
            ),
            row=1, col=1,
        )

    # --- Sell markers ---
    if not trade_log.empty and "exit_date" in trade_log.columns:
        exit_dates = pd.to_datetime(trade_log["exit_date"])
        exit_prices = df.loc[df.index.isin(exit_dates), "High"] * 1.015
        fig.add_trace(
            go.Scatter(
                x=exit_dates,
                y=exit_prices.values,
                mode="markers",
                name="Sell",
                marker=dict(
                    symbol="triangle-down",
                    color=c["sell"],
                    size=12,
                    line=dict(color="white", width=1),
                ),
            ),
            row=1, col=1,
        )

    # --- Volume subplot ---
    if has_volume:
        volume_colors = [
            c["volume_up"] if close >= open_ else c["volume_down"]
            for open_, close in zip(df["Open"], df["Close"])
        ]
        fig.add_trace(
            go.Bar(
                x=df.index, y=df["Volume"],
                name="Volume",
                marker_color=volume_colors,
                showlegend=False,
            ),
            row=volume_row, col=1,
        )

    # --- RSI subplot ---
    if has_rsi:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["RSI"],
                mode="lines", name="RSI",
                line=dict(color=c["rsi"], width=1.5),
            ),
            row=rsi_row, col=1,
        )
        # Overbought / oversold reference lines
        for level, color in [(70, c["sell"]), (30, c["buy"])]:
            fig.add_hline(
                y=level, line_dash="dash",
                line_color=color, opacity=0.6,
                row=rsi_row, col=1,
            )

    # Height scales with the number of subplots
    chart_height = 480 + (120 if has_volume else 0) + (160 if has_rsi else 0)

    fig.update_layout(
        template=template,
        paper_bgcolor=c["bg"],
        plot_bgcolor=c["bg"],
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        height=chart_height,
        bargap=0.0,
        dragmode="zoom",
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=c["grid"], zeroline=False, fixedrange=False)

    return fig


# Plotly.js config to enable wheel/pinch zoom inside the chart area
# (so the mouse wheel / touch pinch zooms the chart instead of scrolling the page)
INTERACTIVE_CHART_CONFIG: dict = {
    "scrollZoom": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}


def equity_curve(
    portfolio_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    strategy_name: str = "Strategy",
    initial_capital: float = 100_000,
) -> go.Figure:
    """
    Line chart showing portfolio value over time vs Buy & Hold benchmark.
    Both curves start from `initial_capital`.

    Parameters
    ----------
    portfolio_df   : DataFrame with 'Portfolio_Value' column (active strategy)
    benchmark_df   : DataFrame with 'Portfolio_Value' column (Buy & Hold)
    strategy_name  : label for the active strategy line
    initial_capital: starting value for annotation
    """
    c = _chart_colors()
    template = get_plotly_template()
    t = get_theme()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=portfolio_df.index,
            y=portfolio_df["Portfolio_Value"],
            mode="lines",
            name=strategy_name,
            line=dict(color=c["strategy"], width=2),
            fill="tozeroy",
            fillcolor=t["neutral_soft"],
        )
    )

    fig.add_trace(
        go.Scatter(
            x=benchmark_df.index,
            y=benchmark_df["Portfolio_Value"],
            mode="lines",
            name="Buy & Hold",
            line=dict(color=c["benchmark"], width=1.5, dash="dash"),
        )
    )

    # Horizontal baseline
    fig.add_hline(
        y=initial_capital,
        line_dash="dot",
        line_color=t["border_strong"],
        annotation_text="Initial Capital",
        annotation_position="bottom right",
    )

    fig.update_layout(
        template=template,
        paper_bgcolor=c["bg"],
        plot_bgcolor=c["bg"],
        title=dict(
            text="Portfolio Value Over Time",
            font=dict(size=16),
            x=0, xanchor="left",
            y=0.97, yanchor="top",
        ),
        xaxis_title=None,
        yaxis_title="Portfolio Value",
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1,
        ),
        margin=dict(l=50, r=30, t=110, b=40),
        height=460,
        hovermode="x unified",
    )
    fig.update_xaxes(
        showgrid=False,
        rangeselector=dict(
            buttons=[
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(count=5, label="5Y", step="year", stepmode="backward"),
                dict(step="all", label="All"),
            ],
            bgcolor=t["panel"],
            activecolor=t["accent"],
            bordercolor=t["border_strong"],
            borderwidth=1,
            font=dict(color=t["text"], size=12),
            xanchor="right", x=1,
            yanchor="bottom", y=1.12,
        ),
    )
    fig.update_yaxes(showgrid=True, gridcolor=c["grid"], tickprefix="₹")

    return fig


def drawdown_chart(portfolio_df: pd.DataFrame, drawdown_series: pd.Series) -> go.Figure:
    """
    Area chart showing the drawdown (%) over time.
    """
    c = _chart_colors()
    template = get_plotly_template()
    t = get_theme()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=drawdown_series.index,
            y=drawdown_series.values,
            mode="lines",
            name="Drawdown %",
            line=dict(color=c["drawdown"], width=1.5),
            fill="tozeroy",
            fillcolor=t["danger_soft"],
        )
    )

    fig.update_layout(
        template=template,
        paper_bgcolor=c["bg"],
        plot_bgcolor=c["bg"],
        title=dict(text="Drawdown Over Time", font=dict(size=16)),
        xaxis_title="Date",
        yaxis_title="Drawdown %",
        margin=dict(l=40, r=40, t=60, b=40),
        height=320,
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor=c["grid"], ticksuffix="%")

    return fig
