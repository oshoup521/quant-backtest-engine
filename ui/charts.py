"""
Plotly Chart Builders
----------------------
All charts return go.Figure objects for use with st.plotly_chart().
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
COLOR_BUY = "#26a641"       # green
COLOR_SELL = "#f85149"      # red
COLOR_STRATEGY = "#58a6ff"  # blue
COLOR_BENCHMARK = "#8b949e" # gray
COLOR_CANDLE_UP = "#26a641"
COLOR_CANDLE_DOWN = "#f85149"
COLOR_SMA_SHORT = "#ffa657"  # orange
COLOR_SMA_LONG = "#d2a8ff"   # purple
COLOR_RSI = "#79c0ff"
COLOR_DRAWDOWN = "#f85149"


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
    has_rsi = "RSI" in df.columns
    has_sma = "SMA_short" in df.columns and "SMA_long" in df.columns

    row_heights = [0.7, 0.3] if has_rsi else [1.0]
    rows = 2 if has_rsi else 1

    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=row_heights,
        subplot_titles=(f"{strategy_name} — Price Chart", "RSI") if has_rsi else (f"{strategy_name} — Price Chart",),
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
            increasing_line_color=COLOR_CANDLE_UP,
            decreasing_line_color=COLOR_CANDLE_DOWN,
            increasing_fillcolor=COLOR_CANDLE_UP,
            decreasing_fillcolor=COLOR_CANDLE_DOWN,
        ),
        row=1, col=1,
    )

    # --- SMA overlays ---
    if has_sma:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["SMA_short"],
                mode="lines", name="SMA Short",
                line=dict(color=COLOR_SMA_SHORT, width=1.5),
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["SMA_long"],
                mode="lines", name="SMA Long",
                line=dict(color=COLOR_SMA_LONG, width=1.5),
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
                    color=COLOR_BUY,
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
                    color=COLOR_SELL,
                    size=12,
                    line=dict(color="white", width=1),
                ),
            ),
            row=1, col=1,
        )

    # --- RSI subplot ---
    if has_rsi:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["RSI"],
                mode="lines", name="RSI",
                line=dict(color=COLOR_RSI, width=1.5),
            ),
            row=2, col=1,
        )
        # Overbought / oversold reference lines
        for level, color in [(70, COLOR_SELL), (30, COLOR_BUY)]:
            fig.add_hline(
                y=level, line_dash="dash",
                line_color=color, opacity=0.6,
                row=2, col=1,
            )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        height=600 if has_rsi else 500,
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#21262d", zeroline=False)

    return fig


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
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=portfolio_df.index,
            y=portfolio_df["Portfolio_Value"],
            mode="lines",
            name=strategy_name,
            line=dict(color=COLOR_STRATEGY, width=2),
            fill="tozeroy",
            fillcolor="rgba(88, 166, 255, 0.05)",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=benchmark_df.index,
            y=benchmark_df["Portfolio_Value"],
            mode="lines",
            name="Buy & Hold",
            line=dict(color=COLOR_BENCHMARK, width=1.5, dash="dash"),
        )
    )

    # Horizontal baseline
    fig.add_hline(
        y=initial_capital,
        line_dash="dot",
        line_color="#3d444d",
        annotation_text="Initial Capital",
        annotation_position="bottom right",
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        title=dict(text="Portfolio Value Over Time", font=dict(size=16)),
        xaxis_title="Date",
        yaxis_title="Portfolio Value",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        height=420,
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#21262d", tickprefix="₹")

    return fig


def drawdown_chart(portfolio_df: pd.DataFrame, drawdown_series: pd.Series) -> go.Figure:
    """
    Area chart showing the drawdown (%) over time.
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=drawdown_series.index,
            y=drawdown_series.values,
            mode="lines",
            name="Drawdown %",
            line=dict(color=COLOR_DRAWDOWN, width=1.5),
            fill="tozeroy",
            fillcolor="rgba(248, 81, 73, 0.15)",
        )
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        title=dict(text="Drawdown Over Time", font=dict(size=16)),
        xaxis_title="Date",
        yaxis_title="Drawdown %",
        margin=dict(l=40, r=40, t=60, b=40),
        height=320,
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#21262d", ticksuffix="%")

    return fig
