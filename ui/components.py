"""
Streamlit UI Components
------------------------
Reusable building blocks for the dashboard: metric cards, sidebar params,
trade log table, and strategy parameter forms.
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from data.fetcher import TICKERS_BY_MARKET
from ui.theme import get_theme


# Quick date-range presets (label → days back from today, None = max)
DATE_PRESETS: dict[str, int | None] = {
    "1Y": 365,
    "3Y": 3 * 365,
    "5Y": 5 * 365,
    "10Y": 10 * 365,
    "Max": None,
}
MAX_LOOKBACK_DAYS = 25 * 365  # ~25y for "Max" preset


# ---------------------------------------------------------------------------
# Metric Cards
# ---------------------------------------------------------------------------

def render_metric_cards(metrics: dict, benchmark_metrics: dict) -> None:
    """
    Render two rows of 4 st.metric() cards showing strategy vs benchmark.
    """
    st.markdown("#### Performance vs Buy & Hold")

    # Row 1 — Return metrics
    c1, c2, c3, c4 = st.columns(4)

    total_delta = metrics["total_return_pct"] - benchmark_metrics["total_return_pct"]
    cagr_delta = metrics["cagr_pct"] - benchmark_metrics["cagr_pct"]
    dd_delta = metrics["max_drawdown_pct"] - benchmark_metrics["max_drawdown_pct"]
    sharpe_delta = metrics["sharpe_ratio"] - benchmark_metrics["sharpe_ratio"]

    c1.metric(
        "Total Return",
        f"{metrics['total_return_pct']:+.2f}%",
        delta=f"{total_delta:+.2f}% vs B&H",
        delta_color="normal",
    )
    c2.metric(
        "CAGR",
        f"{metrics['cagr_pct']:+.2f}%",
        delta=f"{cagr_delta:+.2f}% vs B&H",
        delta_color="normal",
    )
    c3.metric(
        "Max Drawdown",
        f"{metrics['max_drawdown_pct']:.2f}%",
        delta=f"{dd_delta:+.2f}% vs B&H",
        delta_color="inverse",  # less negative drawdown = green
    )
    c4.metric(
        "Sharpe Ratio",
        f"{metrics['sharpe_ratio']:.3f}",
        delta=f"{sharpe_delta:+.3f} vs B&H",
        delta_color="normal",
    )

    st.markdown("")  # spacer

    # Row 2 — Trade statistics
    c5, c6, c7, c8 = st.columns(4)

    c5.metric("Win Rate", f"{metrics['win_rate_pct']:.1f}%")
    c6.metric("Total Trades", str(metrics["total_trades"]))
    c7.metric("Avg Trade Duration", f"{metrics['avg_duration_days']:.0f} days")
    c8.metric(
        "Best / Worst Trade",
        f"{metrics['best_trade_pct']:+.2f}%",
        delta=f"Worst: {metrics['worst_trade_pct']:+.2f}%",
        delta_color="off",
    )


# ---------------------------------------------------------------------------
# Verdict Card
# ---------------------------------------------------------------------------

_SCORE_ICON: dict[str, str] = {"good": "✓", "okay": "•", "bad": "✗"}


def render_verdict_card(verdict: dict) -> None:
    """
    Render the strategy verdict as a styled card with check-by-check breakdown.
    Colors come from the active theme so the card adapts to dark/light mode.
    """
    t = get_theme()

    # Rating-specific accent (border + label color) + soft background tint
    rating_styles = {
        "strong":       {"emoji": "🟢", "label": "STRONG STRATEGY",   "border": t["success"],    "bg": t["success_soft"]},
        "mixed":        {"emoji": "🟡", "label": "MIXED RESULTS",     "border": t["warning"],    "bg": t["warning_soft"]},
        "weak":         {"emoji": "🔴", "label": "WEAK STRATEGY",     "border": t["danger"],     "bg": t["danger_soft"]},
        "insufficient": {"emoji": "⚪", "label": "INSUFFICIENT DATA", "border": t["text_muted"], "bg": t["neutral_soft"]},
    }
    score_color = {"good": t["success"], "okay": t["warning"], "bad": t["danger"]}
    style = rating_styles[verdict["rating"]]

    checks_html = ""
    for check in verdict["checks"]:
        color = score_color[check["score"]]
        icon = _SCORE_ICON[check["score"]]
        checks_html += (
            f'<div style="display:flex; align-items:center; gap:8px; '
            f'padding:6px 0; font-size:0.85rem; color:{t["text"]};">'
            f'<span style="color:{color}; font-weight:700; font-size:1rem; '
            f'min-width:14px; text-align:center;">{icon}</span>'
            f'<span style="color:{t["text_muted"]}; min-width:160px;">{check["name"]}</span>'
            f'<span>{check["message"]}</span>'
            f"</div>"
        )

    st.markdown(
        f"""
        <div style="
            background: {style['bg']};
            border: 1px solid {t['border']};
            border-left: 4px solid {style['border']};
            border-radius: 8px;
            padding: 16px 20px;
            margin: 12px 0 16px 0;
        ">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                <span style="font-size:1.3rem;">{style['emoji']}</span>
                <span style="font-size:0.85rem; font-weight:700; letter-spacing:0.08em;
                             color:{style['border']};">{style['label']}</span>
            </div>
            <div style="color:{t['text']}; font-size:0.95rem; line-height:1.45; margin-bottom:10px;">
                {verdict['headline']}
            </div>
            <div style="border-top:1px solid {t['border']}; padding-top:8px; margin-top:8px;">
                {checks_html}
            </div>
            <div style="color:{t['text_dim']}; font-size:0.72rem; margin-top:10px; font-style:italic;">
                Educational backtest — not financial advice. Past performance is not indicative of future results.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Sidebar — Strategy Parameter Forms
# ---------------------------------------------------------------------------

def render_sidebar() -> dict:
    """
    Render the full sidebar and return a dict of all user-selected params.
    """
    st.sidebar.title("Backtest Configuration")
    st.sidebar.markdown("---")

    # --- Ticker ---
    st.sidebar.subheader("Market")
    ticker_mode = st.sidebar.radio(
        "Ticker input", ["Pick from list", "Type manually"], horizontal=True
    )
    if ticker_mode == "Pick from list":
        market = st.sidebar.selectbox("Market", list(TICKERS_BY_MARKET.keys()))
        group = TICKERS_BY_MARKET[market]
        label = st.sidebar.selectbox("Ticker", list(group.keys()))
        ticker = group[label]
    else:
        ticker = st.sidebar.text_input("Ticker symbol", value="^NSEI").strip().upper()

    st.sidebar.caption(f"Selected: **{ticker}**")

    # --- Date Range ---
    st.sidebar.subheader("Date Range")
    default_end = date.today()

    # Quick presets — single horizontal row of compact buttons
    preset_cols = st.sidebar.columns(len(DATE_PRESETS), gap="small")
    for col, (label, days) in zip(preset_cols, DATE_PRESETS.items()):
        if col.button(label, use_container_width=True, key=f"preset_{label}"):
            lookback = days if days is not None else MAX_LOOKBACK_DAYS
            st.session_state["bt_start_date"] = default_end - timedelta(days=lookback)
            st.session_state["bt_end_date"] = default_end

    # Initialize defaults on first run
    if "bt_start_date" not in st.session_state:
        st.session_state["bt_start_date"] = default_end - timedelta(days=5 * 365)
    if "bt_end_date" not in st.session_state:
        st.session_state["bt_end_date"] = default_end

    col_s, col_e = st.sidebar.columns(2)
    start_date = col_s.date_input(
        "Start", key="bt_start_date", max_value=default_end,
    )
    end_date = col_e.date_input(
        "End", key="bt_end_date", min_value=start_date, max_value=default_end,
    )

    # --- Strategy ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("Strategy")
    strategy = st.sidebar.selectbox(
        "Choose strategy",
        ["Moving Average Crossover", "RSI Mean Reversion", "Buy & Hold"],
    )

    strategy_params = {}

    if strategy == "Moving Average Crossover":
        st.sidebar.markdown("**MA Crossover Parameters**")
        short_window = st.sidebar.slider("Short-term SMA (days)", 5, 100, 50, step=5)
        long_window = st.sidebar.slider("Long-term SMA (days)", 50, 300, 200, step=10)
        if short_window >= long_window:
            st.sidebar.error("Short window must be < Long window")
        strategy_params = {"short_window": short_window, "long_window": long_window}

    elif strategy == "RSI Mean Reversion":
        st.sidebar.markdown("**RSI Parameters**")
        rsi_period = st.sidebar.slider("RSI Period", 5, 30, 14, step=1)
        oversold = st.sidebar.slider("Oversold threshold", 10, 40, 30, step=1)
        overbought = st.sidebar.slider("Overbought threshold", 60, 90, 70, step=1)
        if oversold >= overbought:
            st.sidebar.error("Oversold must be < Overbought")
        strategy_params = {
            "rsi_period": rsi_period,
            "oversold": oversold,
            "overbought": overbought,
        }

    # --- Capital & Costs ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("Capital & Costs")
    initial_capital = st.sidebar.number_input(
        "Initial Capital (₹)", min_value=10_000, max_value=10_000_000,
        value=100_000, step=10_000,
    )
    transaction_cost_pct = st.sidebar.slider(
        "Transaction Cost per leg (%)", 0.0, 1.0, 0.1, step=0.05,
        help="Brokerage + slippage per trade leg. Applied on both entry and exit.",
    )

    st.sidebar.markdown("---")
    run_clicked = st.sidebar.button("Run Backtest", type="primary", use_container_width=True)

    return {
        "ticker": ticker,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "strategy": strategy,
        "strategy_params": strategy_params,
        "initial_capital": float(initial_capital),
        "transaction_cost": transaction_cost_pct / 100,
        "run_clicked": run_clicked,
    }


# ---------------------------------------------------------------------------
# Trade Log Table
# ---------------------------------------------------------------------------

def render_trade_log(trade_log: pd.DataFrame) -> None:
    """
    Render the full trade log inside an expandable section.
    """
    if trade_log.empty:
        st.info("No completed trades were recorded for this strategy and date range.")
        return

    # Quick summary strip above the expander
    wins = (trade_log["return_pct"] > 0).sum()
    losses = (trade_log["return_pct"] <= 0).sum()
    avg_ret = trade_log["return_pct"].mean()
    best = trade_log["return_pct"].max()
    worst = trade_log["return_pct"].min()
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Trades", f"{len(trade_log)}")
    s2.metric("Wins / Losses", f"{wins} / {losses}")
    s3.metric("Avg Return", f"{avg_ret:+.2f}%")
    s4.metric("Best", f"{best:+.2f}%")
    s5.metric("Worst", f"{worst:+.2f}%")

    with st.expander(f"Trade Log — {len(trade_log)} trades", expanded=True):
        display = trade_log.copy()
        display["entry_date"] = pd.to_datetime(display["entry_date"]).dt.strftime("%d %b %Y")
        display["exit_date"] = pd.to_datetime(display["exit_date"]).dt.strftime("%d %b %Y")
        display.columns = [
            "Entry Date", "Entry Price", "Exit Date", "Exit Price",
            "Return %", "Type", "Duration",
        ]

        t = get_theme()
        pos_color, neg_color, neutral_color = t["success"], t["danger"], t["text_muted"]

        def _color_return(val: float) -> str:
            if val > 0:
                return f"color: {pos_color}; font-weight: 600;"
            if val < 0:
                return f"color: {neg_color}; font-weight: 600;"
            return f"color: {neutral_color};"

        styled = (
            display.style
            .format({
                "Entry Price": "₹{:,.2f}",
                "Exit Price": "₹{:,.2f}",
                "Return %": "{:+.2f}%",
                "Duration": "{:.0f} days",
            })
            .map(_color_return, subset=["Return %"])
        )

        st.dataframe(styled, use_container_width=True, hide_index=True)

        # Download button
        csv = trade_log.to_csv(index=False)
        st.download_button(
            label="Download trade log as CSV",
            data=csv,
            file_name="trade_log.csv",
            mime="text/csv",
        )
