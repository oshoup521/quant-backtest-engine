# Quant Backtest Engine — CLAUDE.md

## Project Overview

A professional-grade **Algorithmic Trading Backtesting Engine** built with Python and Streamlit. This is a portfolio-quality project designed to demonstrate deep knowledge of financial data pipelines, quantitative metrics, and interactive FinTech dashboards.

**Target audience:** Recruiters and engineers in quant finance, data engineering, or full-stack Python roles.

---

## Tech Stack

| Layer | Library |
|---|---|
| UI / Dashboard | `streamlit` |
| Data Fetching | `yfinance` |
| Data Manipulation | `pandas`, `numpy` |
| Charting | `plotly` (graph_objects + express) |
| Caching | `@st.cache_data` (Streamlit native) |

### Install

```bash
pip install streamlit yfinance pandas numpy plotly pytest
```

Run the app:

```bash
streamlit run app.py
```

---

## Project Structure

```
quant-backtest-engine/
├── app.py                  # Streamlit entry point — sidebar + page routing
├── CLAUDE.md
├── requirements.txt
│
├── data/
│   └── fetcher.py          # yfinance wrapper with @st.cache_data
│
├── strategies/
│   ├── __init__.py
│   ├── ma_crossover.py     # Moving Average Crossover strategy
│   ├── rsi_mean_reversion.py  # RSI Mean Reversion strategy
│   └── buy_and_hold.py     # Benchmark strategy
│
├── engine/
│   ├── __init__.py
│   ├── backtest.py         # Core backtesting loop (signal → trade log)
│   └── metrics.py          # CAGR, Max Drawdown, Win Rate, etc.
│
└── ui/
    ├── __init__.py
    ├── charts.py           # Plotly candlestick + equity curve builders
    └── components.py       # Reusable Streamlit metric cards, trade log table
```

---

## Module 1 — Data Ingestion Engine (`data/fetcher.py`)

### Responsibilities
- Fetch OHLCV data via `yfinance.download()`
- Support multi-market tickers: Indian (RELIANCE.NS, ^NSEI), US (AAPL, SPY), global indices
- Accept user-defined date ranges (start_date, end_date)
- Cache results with `@st.cache_data(ttl=3600)` — no redundant network calls during UI interaction

### Key function signature

```python
@st.cache_data(ttl=3600)
def fetch_ohlcv(ticker: str, start: str, end: str) -> pd.DataFrame:
    """
    Returns DataFrame with columns: [Open, High, Low, Close, Volume]
    Index: DatetimeIndex
    Raises ValueError if ticker is invalid or data is empty.
    """
```

### Ticker examples to support
- `^NSEI` — Nifty 50 index
- `RELIANCE.NS` — NSE stock
- `AAPL`, `SPY` — US stocks / ETFs
- `^GSPC` — S&P 500

---

## Module 2 — Strategy Logic (`strategies/`)

All strategies share a **common interface**:

```python
def generate_signals(df: pd.DataFrame, **params) -> pd.DataFrame:
    """
    Input:  OHLCV DataFrame
    Output: same DataFrame with added columns:
              - 'Signal'   : 1 (Buy), -1 (Sell), 0 (Hold)
              - 'Position' : running position (1 = in trade, 0 = out)
    """
```

### Strategy 1 — Moving Average Crossover (`ma_crossover.py`)

**Logic:**
- Compute `SMA_short` (e.g., 50-day) and `SMA_long` (e.g., 200-day)
- **Buy signal:** `SMA_short` crosses **above** `SMA_long` (Golden Cross)
- **Sell signal:** `SMA_short` crosses **below** `SMA_long` (Death Cross)

**User-configurable params (Streamlit sliders):**
- `short_window`: int, default 50, range 5–100
- `long_window`: int, default 200, range 50–300

### Strategy 2 — RSI Mean Reversion (`rsi_mean_reversion.py`)

**Logic:**
- Compute 14-period RSI using Wilder's smoothing (EMA-based)
- **Buy signal:** RSI crosses **below** oversold threshold (e.g., 30)
- **Sell signal:** RSI crosses **above** overbought threshold (e.g., 70)

**User-configurable params:**
- `rsi_period`: int, default 14, range 5–30
- `oversold`: int, default 30, range 10–40
- `overbought`: int, default 70, range 60–90

**RSI formula:**
```
RS  = Average Gain / Average Loss  (over rsi_period)
RSI = 100 - (100 / (1 + RS))
```

### Strategy 3 — Buy & Hold Benchmark (`buy_and_hold.py`)

**Logic:**
- Single Buy signal on first available date, hold till end
- Used as the passive benchmark for all comparison metrics
- Always rendered as a separate equity curve line (dashed gray)

---

## Module 3 — Backtesting Engine (`engine/backtest.py`)

### Core loop

```python
def run_backtest(
    df: pd.DataFrame,           # OHLCV + Signal columns
    initial_capital: float,     # e.g., 100000
    transaction_cost: float,    # e.g., 0.001 = 0.1% per trade
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns:
        portfolio_df  — daily portfolio value indexed by date
        trade_log_df  — one row per completed trade
    """
```

### Trade log schema

| Column | Type | Description |
|---|---|---|
| `entry_date` | datetime | Date position was opened |
| `entry_price` | float | Close price on entry |
| `exit_date` | datetime | Date position was closed |
| `exit_price` | float | Close price on exit |
| `return_pct` | float | (exit - entry) / entry * 100, net of costs |
| `trade_type` | str | "Long" (only long trades in v1) |

### Transaction cost / slippage

Apply on both entry and exit:

```python
effective_entry = entry_price * (1 + transaction_cost)
effective_exit  = exit_price  * (1 - transaction_cost)
```

---

## Module 4 — Quantitative Metrics (`engine/metrics.py`)

All metrics computed from `portfolio_df` (daily portfolio value series).

### Required metrics

| Metric | Formula / Notes |
|---|---|
| **Total Return %** | `(final_value - initial_capital) / initial_capital * 100` |
| **CAGR** | `(final_value / initial_capital) ^ (1 / years) - 1` |
| **Max Drawdown** | `min((portfolio - rolling_max) / rolling_max)` — most negative drawdown |
| **Sharpe Ratio** | `(mean_daily_return - rf_rate/252) / std_daily_return * sqrt(252)` — use rf=0.06 for India |
| **Win Rate** | `profitable_trades / total_trades * 100` |
| **Total Trades** | Count of completed round-trip trades |
| **Avg Trade Duration** | Mean days between entry and exit |

```python
def compute_metrics(
    portfolio_df: pd.DataFrame,
    trade_log_df: pd.DataFrame,
    initial_capital: float,
    risk_free_rate: float = 0.06,
) -> dict:
    """Returns dict of all metrics above."""
```

---

## Module 5 — UI / Visualization (`ui/`)

### `charts.py` — Plotly chart builders

#### 1. Candlestick chart with trade markers

```python
def candlestick_with_signals(df: pd.DataFrame, trade_log: pd.DataFrame) -> go.Figure:
```

- `go.Candlestick` for OHLC price action
- Green upward triangle markers on `entry_date` rows (Buy signals)
- Red downward triangle markers on `exit_date` rows (Sell signals)
- Overlay SMA lines if strategy is MA Crossover

#### 2. Equity curve chart

```python
def equity_curve(portfolio_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> go.Figure:
```

- Solid colored line for active strategy portfolio value
- Dashed gray line for Buy & Hold benchmark
- Both starting from same `initial_capital`
- Y-axis: portfolio value in INR / USD

### `components.py` — Streamlit UI elements

- `render_metric_cards(metrics: dict)` — 4-column `st.metric()` grid
- `render_trade_log(trade_log: pd.DataFrame)` — `st.expander` wrapping styled `st.dataframe`
- `render_sidebar()` — Returns ticker, date, strategy params, costs, and run trigger

---

## `app.py` — Main Streamlit App Layout

### Sidebar controls

```
[Ticker Input]          e.g. ^NSEI
[Start Date]            st.date_input
[End Date]              st.date_input
[Strategy Selector]     st.selectbox — MA Crossover / RSI / Buy & Hold
[Strategy Params]       Dynamic sliders (rendered inside components.render_sidebar)
[Initial Capital]       st.number_input, default 100000
[Transaction Cost %]    st.slider, 0.0–1.0%, default 0.1%
[Run Backtest Button]   st.button
```

### Main panel layout (after Run)

```
[st.title]  Strategy Name — Ticker (Date Range)

[Row 1]  Metric cards: Total Return | CAGR | Max Drawdown | Sharpe Ratio
[Row 2]  Metric cards: Win Rate | Total Trades | Avg Duration | vs Benchmark

[Tab 1: Price Chart]   Candlestick with buy/sell markers
[Tab 2: Equity Curve]  Portfolio vs Buy & Hold over time
[Tab 3: Trade Log]     Expandable dataframe of all trades
```

---

## Coding Conventions

- **No global state** — pass data through function arguments, never module-level variables
- **Separation of concerns** — strategies only return signal columns, never compute metrics
- **Defensive data handling** — always validate that fetched DataFrame is non-empty before processing; raise `ValueError` with a clear message
- **Type hints** on all public functions
- **No magic numbers** — all default parameter values defined as constants at the top of each file
- **Plotly, not matplotlib** — all charts must be interactive (`st.plotly_chart(fig, use_container_width=True)`)
- **Cache at the data layer only** — `@st.cache_data` only in `data/fetcher.py`, never on strategy or metrics functions

---

## Known Edge Cases to Handle

| Case | Handling |
|---|---|
| Ticker not found on yfinance | Show `st.error()`, halt execution gracefully |
| Not enough data for long SMA (e.g., 200-day on 1-year data) | Warn user, suggest longer date range |
| No trades generated by strategy | Show `st.warning("No trades were triggered...")` |
| NaN values in OHLCV (market holidays) | `df.ffill()` then `df.dropna()` |
| Short window >= long window (MA strategy) | Validate in sidebar, show `st.error` before running |

---

## Future Enhancements (v2 scope — do not implement now)

- Bollinger Bands strategy
- Multi-ticker portfolio backtesting (correlation matrix)
- Monte Carlo simulation for drawdown distribution
- Walk-forward optimization to avoid overfitting

---

## Sample Ticker Cheat Sheet

| Market | Ticker | Description |
|---|---|---|
| India Index | `^NSEI` | Nifty 50 |
| India Index | `^BSESN` | BSE Sensex |
| India Stock | `RELIANCE.NS` | Reliance Industries |
| India Stock | `TCS.NS` | Tata Consultancy Services |
| US Index | `^GSPC` | S&P 500 |
| US ETF | `SPY` | S&P 500 ETF |
| US Stock | `AAPL` | Apple Inc. |
| Crypto | `BTC-USD` | Bitcoin |
