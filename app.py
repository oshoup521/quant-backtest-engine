"""
Quant Backtest Engine — Main Streamlit Application
----------------------------------------------------
Entry point. Run with:  streamlit run app.py
"""

from pathlib import Path

import streamlit as st
import pandas as pd
from PIL import Image

from data.fetcher import (
    fetch_ohlcv,
    validate_date_range,
    detect_market,
    market_risk_free_rate,
)
from ui.theme import get_theme, DEFAULT_MODE
from strategies.ma_crossover import generate_signals as ma_signals
from strategies.rsi_mean_reversion import generate_signals as rsi_signals
from strategies.buy_and_hold import generate_signals as bh_signals
from engine.backtest import run_backtest
from engine.metrics import compute_metrics, compute_drawdown_series
from engine.verdict import evaluate_strategy
from ui.components import (
    render_sidebar,
    render_metric_cards,
    render_trade_log,
    render_verdict_card,
)
from ui.charts import (
    candlestick_with_signals,
    equity_curve,
    drawdown_chart,
    INTERACTIVE_CHART_CONFIG,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

FAVICON_PATH = Path(__file__).parent / "assets" / "favicon.png"
_page_icon = Image.open(FAVICON_PATH) if FAVICON_PATH.exists() else "📈"

st.set_page_config(
    page_title="Quant Backtest Engine",
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Theme — initialize mode in session_state so all components see the same value
# ---------------------------------------------------------------------------

if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = DEFAULT_MODE
T = get_theme()

# ---------------------------------------------------------------------------
# Custom CSS — driven entirely by the active theme palette
# ---------------------------------------------------------------------------

st.markdown(
    f"""
    <style>
        /* Global background */
        .stApp {{ background-color: {T['bg']}; color: {T['text']}; }}

        /* Sticky header band — anchored under .sticky-header marker */
        .sticky-header {{
            position: sticky;
            top: 0;
            z-index: 999;
            background: {T['bg']};
            border-bottom: 1px solid {T['border']};
            margin: -1rem -1rem 1rem -1rem;
            padding: 12px 1rem 8px 1rem;
            backdrop-filter: blur(6px);
        }}
        .sticky-header h1 {{
            font-size: 1.5rem !important;
            font-weight: 700;
            color: {T['text']};
            margin: 0 !important;
            line-height: 1.2;
        }}
        .sticky-header .subtitle {{
            color: {T['text_muted']};
            font-size: 0.82rem;
            margin-top: 2px;
        }}

        /* Metric cards */
        [data-testid="stMetric"] {{
            background: {T['panel']};
            border: 1px solid {T['border']};
            border-radius: 8px;
            padding: 16px;
        }}
        [data-testid="stMetricLabel"] {{ color: {T['text_muted']}; font-size: 0.78rem; }}
        [data-testid="stMetricValue"] {{ color: {T['text']}; font-size: 1.4rem; font-weight: 600; }}

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
        .stTabs [data-baseweb="tab"] {{
            background: {T['panel']};
            border: 1px solid {T['border']};
            border-radius: 6px;
            padding: 6px 18px;
            color: {T['text_muted']};
        }}
        .stTabs [aria-selected="true"] {{
            background: {T['accent']} !important;
            color: white !important;
            border-color: {T['accent']} !important;
        }}

        /* Sidebar */
        [data-testid="stSidebar"] {{ background-color: {T['panel']}; }}

        /* Primary "Run Backtest" button — green, full size */
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {{
            background-color: {T['btn_primary_bg']};
            color: white;
            border: none;
            font-weight: 600;
        }}
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:hover {{
            background-color: {T['btn_primary_hover']};
        }}

        /* Secondary buttons in sidebar (date-range presets) — compact */
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {{
            padding: 4px 6px;
            min-height: 30px;
            font-size: 0.78rem;
            font-weight: 600;
            line-height: 1;
            white-space: nowrap;
            background-color: {T['btn_secondary_bg']};
            color: {T['text']};
            border: 1px solid {T['border_strong']};
        }}
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {{
            background-color: {T['btn_secondary_hover']};
            border-color: {T['accent']};
        }}

        /* Divider */
        hr {{ border-color: {T['border']}; }}

        /* Expander */
        [data-testid="stExpander"] {{
            background: {T['panel']};
            border: 1px solid {T['border']};
            border-radius: 8px;
        }}

        /* Let Plotly capture pinch / wheel gestures inside charts so the page
           doesn't scroll while the user is zooming the chart on mobile. */
        [data-testid="stPlotlyChart"] {{
            touch-action: none;
        }}

        /* Plotly range-selector chips on equity curve */
        [data-testid="stPlotlyChart"] .rangeselector .button text {{
            font-size: 12px !important;
        }}
        [data-testid="stPlotlyChart"] .rangeselector .button rect {{
            rx: 4;
            ry: 4;
        }}

        /* Input fields (date, text, number) — readable on the active background */
        [data-testid="stDateInput"] input,
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input {{
            color: {T['text']} !important;
            background-color: {T['bg']} !important;
            -webkit-text-fill-color: {T['text']} !important;
        }}
        [data-testid="stDateInput"] input::placeholder,
        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stNumberInput"] input::placeholder {{
            color: {T['text_dim']} !important;
        }}
        /* Selectbox displayed value */
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
            color: {T['text']} !important;
        }}

        /* Pointer cursor on interactive controls */
        [data-testid="stSelectbox"] div[data-baseweb="select"],
        [data-testid="stSelectbox"] div[data-baseweb="select"] *,
        [data-baseweb="popover"] li,
        [data-testid="stRadio"] label,
        [data-testid="stDateInput"] input,
        [data-testid="stExpander"] summary,
        [data-testid="stSlider"] [role="slider"] {{
            cursor: pointer !important;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sticky Header — title on left, theme toggle on right
# ---------------------------------------------------------------------------

# Marker div so the CSS selector .sticky-header applies styling to the
# Streamlit container that immediately follows.
st.markdown('<div class="sticky-header"></div>', unsafe_allow_html=True)

with st.container():
    h_left, h_right = st.columns([6, 1])
    with h_left:
        st.markdown(
            f"""
            <h1>📈 Quant Backtest Engine</h1>
            <div class="subtitle">Test algorithmic trading strategies against historical market data</div>
            """,
            unsafe_allow_html=True,
        )
    with h_right:
        # Radio drives the theme; selecting a new value triggers a rerun
        # which re-reads the theme on the next render.
        new_mode = st.radio(
            "Theme",
            options=["dark", "light"],
            format_func=lambda m: "🌙 Dark" if m == "dark" else "☀️ Light",
            index=0 if st.session_state["theme_mode"] == "dark" else 1,
            horizontal=True,
            label_visibility="collapsed",
            key="theme_radio",
        )
        if new_mode != st.session_state["theme_mode"]:
            st.session_state["theme_mode"] = new_mode
            st.rerun()

# ---------------------------------------------------------------------------
# Sidebar — collect all parameters
# ---------------------------------------------------------------------------

params = render_sidebar()

# ---------------------------------------------------------------------------
# Main panel — only execute after "Run Backtest" is clicked
# ---------------------------------------------------------------------------

if not params["run_clicked"]:
    # Landing state — theme-aware feature cards
    _card = (
        f'background:{T["panel"]}; border:1px solid {T["border"]}; '
        f'border-radius:8px; padding:16px 24px; min-width:160px;'
    )
    st.markdown(
        f"""
        <div style="text-align:center; padding: 80px 0; color: {T['text_muted']};">
            <div style="font-size: 3.5rem;">📊</div>
            <h3 style="color: {T['text']}; margin-top: 12px;">Configure & Run Your Backtest</h3>
            <p>Select a ticker, date range, and strategy in the sidebar, then click <strong>Run Backtest</strong>.</p>
            <br/>
            <div style="display:flex; justify-content:center; gap:40px; flex-wrap:wrap;">
                <div style="{_card}">
                    <div style="font-size:1.5rem;">📡</div>
                    <div style="color:{T['text']}; font-weight:600; margin-top:8px;">Live Market Data</div>
                    <div style="font-size:0.8rem;">Powered by Yahoo Finance</div>
                </div>
                <div style="{_card}">
                    <div style="font-size:1.5rem;">⚡</div>
                    <div style="color:{T['text']}; font-weight:600; margin-top:8px;">3 Strategies</div>
                    <div style="font-size:0.8rem;">MA Crossover · RSI · Buy & Hold</div>
                </div>
                <div style="{_card}">
                    <div style="font-size:1.5rem;">📐</div>
                    <div style="color:{T['text']}; font-weight:600; margin-top:8px;">Quant Metrics</div>
                    <div style="font-size:0.8rem;">CAGR · Drawdown · Sharpe</div>
                </div>
                <div style="{_card}">
                    <div style="font-size:1.5rem;">💸</div>
                    <div style="color:{T['text']}; font-weight:600; margin-top:8px;">Realistic Costs</div>
                    <div style="font-size:0.8rem;">Brokerage & slippage built-in</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# ---------------------------------------------------------------------------
# Run backtest
# ---------------------------------------------------------------------------

ticker = params["ticker"]
start_date = params["start_date"]
end_date = params["end_date"]
strategy_name = params["strategy"]
strategy_params = params["strategy_params"]
initial_capital = params["initial_capital"]
transaction_cost = params["transaction_cost"]

try:
    validate_date_range(start_date, end_date)
except ValueError as e:
    st.error(str(e))
    st.stop()

# Fetch data
try:
    df_raw = fetch_ohlcv(ticker, start_date, end_date)
except ValueError as e:
    st.error(f"Data fetch failed: {e}")
    st.stop()

# Apply strategy signals
try:
    if strategy_name == "Moving Average Crossover":
        df_signals = ma_signals(df_raw, **strategy_params)
    elif strategy_name == "RSI Mean Reversion":
        df_signals = rsi_signals(df_raw, **strategy_params)
    else:
        df_signals = bh_signals(df_raw)
except ValueError as e:
    st.error(str(e))
    st.stop()

# Run backtest for active strategy
portfolio_df, trade_log_df = run_backtest(df_signals, initial_capital, transaction_cost)

# Run Buy & Hold benchmark (always)
df_bh = bh_signals(df_raw)
bh_portfolio_df, _ = run_backtest(df_bh, initial_capital, transaction_cost=0.0)

# Compute metrics — risk-free rate auto-selected per market
rf_rate = market_risk_free_rate(ticker)
metrics = compute_metrics(portfolio_df, trade_log_df, initial_capital, risk_free_rate=rf_rate)
bh_metrics = compute_metrics(bh_portfolio_df, pd.DataFrame(), initial_capital, risk_free_rate=rf_rate)
drawdown_series = compute_drawdown_series(portfolio_df)

# Verdict — only meaningful when the active strategy isn't B&H itself
verdict = (
    evaluate_strategy(metrics, bh_metrics)
    if strategy_name != "Buy & Hold"
    else None
)

# ---------------------------------------------------------------------------
# Results header
# ---------------------------------------------------------------------------

# Build "info pills" describing the run config (params, capital, costs)
def _pill(label: str, value: str, accent: str) -> str:
    return (
        f'<span style="display:inline-block; background:{T["panel"]}; '
        f'border:1px solid {T["border"]}; border-left:3px solid {accent}; '
        f'border-radius:6px; padding:4px 10px; margin:4px 6px 0 0; '
        f'font-size:0.78rem; color:{T["text"]};">'
        f'<span style="color:{T["text_muted"]};">{label}</span> '
        f'<strong>{value}</strong></span>'
    )


pills_html = ""
if strategy_name == "Moving Average Crossover":
    pills_html += _pill("SMA", f"{strategy_params['short_window']} / {strategy_params['long_window']}", T["orange"])
elif strategy_name == "RSI Mean Reversion":
    pills_html += _pill("RSI", f"{strategy_params['rsi_period']} · {strategy_params['oversold']}/{strategy_params['overbought']}", T["cyan"])
pills_html += _pill("Capital", f"₹{initial_capital:,.0f}", T["success"])
pills_html += _pill("Cost / leg", f"{transaction_cost * 100:.2f}%", T["purple"])
pills_html += _pill("Risk-free", f"{rf_rate * 100:.1f}% ({detect_market(ticker)})", T["link"])
pills_html += _pill("Bars", f"{len(df_signals):,}", T["text_muted"])

st.markdown(
    f"""
    <div style="padding: 8px 0 4px 0;">
        <h2 style="font-size:1.5rem; color:{T['text']}; margin:0;">
            {strategy_name} &nbsp;·&nbsp;
            <span style="color:{T['link']};">{ticker}</span>
            &nbsp;·&nbsp;
            <span style="color:{T['text_muted']}; font-size:1rem;">{start_date} → {end_date}</span>
        </h2>
        <div style="margin-top:8px;">{pills_html}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if trade_log_df.empty and strategy_name != "Buy & Hold":
    st.warning(
        "No trades were triggered for this strategy in the selected date range. "
        "Try a wider date range or different parameters."
    )

# ---------------------------------------------------------------------------
# Verdict card
# ---------------------------------------------------------------------------

if verdict is not None:
    render_verdict_card(verdict)

# ---------------------------------------------------------------------------
# Metric Cards
# ---------------------------------------------------------------------------

render_metric_cards(metrics, bh_metrics)

st.markdown("<hr/>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tabs — Price Chart | Equity Curve | Drawdown | Trade Log
# ---------------------------------------------------------------------------

tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Price Chart", "💰 Equity Curve", "📉 Drawdown", "📋 Trade Log"]
)

with tab1:
    fig_candle = candlestick_with_signals(df_signals, trade_log_df, strategy_name)
    st.plotly_chart(fig_candle, use_container_width=True, config=INTERACTIVE_CHART_CONFIG)
    st.caption("Tip: scroll / pinch inside the chart to zoom · drag to pan · double-click to reset.")

with tab2:
    fig_equity = equity_curve(
        portfolio_df, bh_portfolio_df, strategy_name, initial_capital
    )
    st.plotly_chart(fig_equity, use_container_width=True, config=INTERACTIVE_CHART_CONFIG)

    # Summary comparison table
    comp_data = {
        "Metric": ["Total Return", "CAGR", "Max Drawdown", "Sharpe Ratio"],
        strategy_name: [
            f"{metrics['total_return_pct']:+.2f}%",
            f"{metrics['cagr_pct']:+.2f}%",
            f"{metrics['max_drawdown_pct']:.2f}%",
            f"{metrics['sharpe_ratio']:.3f}",
        ],
        "Buy & Hold": [
            f"{bh_metrics['total_return_pct']:+.2f}%",
            f"{bh_metrics['cagr_pct']:+.2f}%",
            f"{bh_metrics['max_drawdown_pct']:.2f}%",
            f"{bh_metrics['sharpe_ratio']:.3f}",
        ],
    }
    st.dataframe(
        pd.DataFrame(comp_data),
        use_container_width=True,
        hide_index=True,
    )

with tab3:
    fig_dd = drawdown_chart(portfolio_df, drawdown_series)
    st.plotly_chart(fig_dd, use_container_width=True, config=INTERACTIVE_CHART_CONFIG)
    st.caption(
        f"Maximum Drawdown: **{metrics['max_drawdown_pct']:.2f}%** "
        f"(Buy & Hold: {bh_metrics['max_drawdown_pct']:.2f}%)"
    )

with tab4:
    render_trade_log(trade_log_df)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown(
    """
    <hr/>
    <div style="text-align:center; color:#8b949e; font-size:0.78rem; padding: 8px 0;">
        Data sourced from Yahoo Finance via yfinance &nbsp;·&nbsp;
        Past performance is not indicative of future results &nbsp;·&nbsp;
        For educational purposes only
    </div>
    """,
    unsafe_allow_html=True,
)
