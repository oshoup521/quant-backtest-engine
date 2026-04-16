# Quant Backtest Engine

Interactive Streamlit app to backtest trading strategies on Yahoo Finance data.

## Features

- Historical OHLCV fetch with caching (`yfinance` + `@st.cache_data`)
- Strategies:
  - Moving Average Crossover
  - RSI Mean Reversion
  - Buy & Hold benchmark
- Backtest engine with transaction cost modeling
- Metrics: Total Return, CAGR, Max Drawdown, Sharpe, Win Rate
- Interactive charts (candlestick, equity curve, drawdown)
- Trade log table + CSV download

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

## Tests

```bash
pytest -q
```

## Project Structure

```text
quant-backtest-engine/
├── app.py
├── requirements.txt
├── data/
├── strategies/
├── engine/
├── ui/
└── tests/
```
