"""
Quant Backtest Engine — Main Streamlit Application
----------------------------------------------------
Entry point. Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd

from data.fetcher import fetch_ohlcv, validate_date_range
from strategies.ma_crossover import generate_signals as ma_signals
from strategies.rsi_mean_reversion import generate_signals as rsi_signals
from strategies.buy_and_hold import generate_signals as bh_signals
from engine.backtest import run_backtest
from engine.metrics import compute_metrics, compute_drawdown_series
from ui.components import render_sidebar, render_metric_cards, render_trade_log
from ui.charts import (
    candlestick_with_signals,
    equity_curve,
    drawdown_chart,
    INTERACTIVE_CHART_CONFIG,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Quant Backtest Engine",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — dark FinTech aesthetic
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
        /* Global background */
        .stApp { background-color: #0d1117; color: #e6edf3; }

        /* Metric cards */
        [data-testid="stMetric"] {
            background: #161b22;
            border: 1px solid #21262d;
            border-radius: 8px;
            padding: 16px;
        }
        [data-testid="stMetricLabel"] { color: #8b949e; font-size: 0.78rem; }
        [data-testid="stMetricValue"] { color: #e6edf3; font-size: 1.4rem; font-weight: 600; }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] {
            background: #161b22;
            border: 1px solid #21262d;
            border-radius: 6px;
            padding: 6px 18px;
            color: #8b949e;
        }
        .stTabs [aria-selected="true"] {
            background: #1f6feb !important;
            color: white !important;
            border-color: #1f6feb !important;
        }

        /* Sidebar */
        [data-testid="stSidebar"] { background-color: #161b22; }

        /* Primary "Run Backtest" button — green, full size */
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
            background-color: #238636;
            color: white;
            border: none;
            font-weight: 600;
        }
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:hover {
            background-color: #2ea043;
        }

        /* Secondary buttons in sidebar (date-range presets) — compact */
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
            padding: 4px 6px;
            min-height: 30px;
            font-size: 0.78rem;
            font-weight: 600;
            line-height: 1;
            white-space: nowrap;
            background-color: #21262d;
            color: #e6edf3;
            border: 1px solid #30363d;
        }
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {
            background-color: #30363d;
            border-color: #1f6feb;
        }

        /* Divider */
        hr { border-color: #21262d; }

        /* Expander */
        [data-testid="stExpander"] {
            background: #161b22;
            border: 1px solid #21262d;
            border-radius: 8px;
        }

        /* Let Plotly capture pinch / wheel gestures inside charts so the page
           doesn't scroll while the user is zooming the chart on mobile. */
        [data-testid="stPlotlyChart"] {
            touch-action: none;
        }

        /* Pointer cursor on interactive controls (selectbox, radio, slider thumb,
           date picker, expanders) — Streamlit defaults these to the text I-beam. */
        [data-testid="stSelectbox"] div[data-baseweb="select"],
        [data-testid="stSelectbox"] div[data-baseweb="select"] *,
        [data-baseweb="popover"] li,
        [data-testid="stRadio"] label,
        [data-testid="stDateInput"] input,
        [data-testid="stExpander"] summary,
        [data-testid="stSlider"] [role="slider"] {
            cursor: pointer !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div style="padding: 16px 0 8px 0;">
        <h1 style="font-size:2rem; font-weight:700; color:#e6edf3; margin:0;">
            📈 Quant Backtest Engine
        </h1>
        <p style="color:#8b949e; margin:4px 0 0 0; font-size:0.95rem;">
            Test algorithmic trading strategies against historical market data
        </p>
    </div>
    <hr/>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar — collect all parameters
# ---------------------------------------------------------------------------

params = render_sidebar()

# ---------------------------------------------------------------------------
# Main panel — only execute after "Run Backtest" is clicked
# ---------------------------------------------------------------------------

if not params["run_clicked"]:
    # Landing state
    st.markdown(
        """
        <div style="text-align:center; padding: 80px 0; color: #8b949e;">
            <div style="font-size: 3.5rem;">📊</div>
            <h3 style="color: #e6edf3; margin-top: 12px;">Configure & Run Your Backtest</h3>
            <p>Select a ticker, date range, and strategy in the sidebar, then click <strong>Run Backtest</strong>.</p>
            <br/>
            <div style="display:flex; justify-content:center; gap:40px; flex-wrap:wrap;">
                <div style="background:#161b22; border:1px solid #21262d; border-radius:8px; padding:16px 24px; min-width:160px;">
                    <div style="font-size:1.5rem;">📡</div>
                    <div style="color:#e6edf3; font-weight:600; margin-top:8px;">Live Market Data</div>
                    <div style="font-size:0.8rem;">Powered by Yahoo Finance</div>
                </div>
                <div style="background:#161b22; border:1px solid #21262d; border-radius:8px; padding:16px 24px; min-width:160px;">
                    <div style="font-size:1.5rem;">⚡</div>
                    <div style="color:#e6edf3; font-weight:600; margin-top:8px;">3 Strategies</div>
                    <div style="font-size:0.8rem;">MA Crossover · RSI · Buy & Hold</div>
                </div>
                <div style="background:#161b22; border:1px solid #21262d; border-radius:8px; padding:16px 24px; min-width:160px;">
                    <div style="font-size:1.5rem;">📐</div>
                    <div style="color:#e6edf3; font-weight:600; margin-top:8px;">Quant Metrics</div>
                    <div style="font-size:0.8rem;">CAGR · Drawdown · Sharpe</div>
                </div>
                <div style="background:#161b22; border:1px solid #21262d; border-radius:8px; padding:16px 24px; min-width:160px;">
                    <div style="font-size:1.5rem;">💸</div>
                    <div style="color:#e6edf3; font-weight:600; margin-top:8px;">Realistic Costs</div>
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

# Compute metrics
metrics = compute_metrics(portfolio_df, trade_log_df, initial_capital)
bh_metrics = compute_metrics(bh_portfolio_df, pd.DataFrame(), initial_capital)
drawdown_series = compute_drawdown_series(portfolio_df)

# ---------------------------------------------------------------------------
# Results header
# ---------------------------------------------------------------------------

# Build "info pills" describing the run config (params, capital, costs)
def _pill(label: str, value: str, accent: str = "#1f6feb") -> str:
    return (
        f'<span style="display:inline-block; background:#161b22; '
        f'border:1px solid #21262d; border-left:3px solid {accent}; '
        f'border-radius:6px; padding:4px 10px; margin:4px 6px 0 0; '
        f'font-size:0.78rem; color:#e6edf3;">'
        f'<span style="color:#8b949e;">{label}</span> '
        f'<strong>{value}</strong></span>'
    )


pills_html = ""
if strategy_name == "Moving Average Crossover":
    pills_html += _pill("SMA", f"{strategy_params['short_window']} / {strategy_params['long_window']}", "#ffa657")
elif strategy_name == "RSI Mean Reversion":
    pills_html += _pill("RSI", f"{strategy_params['rsi_period']} · {strategy_params['oversold']}/{strategy_params['overbought']}", "#79c0ff")
pills_html += _pill("Capital", f"₹{initial_capital:,.0f}", "#26a641")
pills_html += _pill("Cost / leg", f"{transaction_cost * 100:.2f}%", "#d2a8ff")
pills_html += _pill("Bars", f"{len(df_signals):,}", "#8b949e")

st.markdown(
    f"""
    <div style="padding: 8px 0 4px 0;">
        <h2 style="font-size:1.5rem; color:#e6edf3; margin:0;">
            {strategy_name} &nbsp;·&nbsp;
            <span style="color:#58a6ff;">{ticker}</span>
            &nbsp;·&nbsp;
            <span style="color:#8b949e; font-size:1rem;">{start_date} → {end_date}</span>
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
