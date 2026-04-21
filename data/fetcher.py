"""
Data Ingestion Engine
---------------------
Fetches historical OHLCV data from Yahoo Finance with Streamlit caching.
Supports multi-market tickers: Indian (NSE/BSE), US, global indices, crypto.
"""

import streamlit as st
import yfinance as yf
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TICKERS_BY_MARKET: dict[str, dict[str, str]] = {
    "India — Indices": {
        "Nifty 50 (^NSEI)": "^NSEI",
        "BSE Sensex (^BSESN)": "^BSESN",
        "Bank Nifty (^NSEBANK)": "^NSEBANK",
    },
    "India — Stocks": {
        "Reliance (RELIANCE.NS)": "RELIANCE.NS",
        "TCS (TCS.NS)": "TCS.NS",
        "HDFC Bank (HDFCBANK.NS)": "HDFCBANK.NS",
        "Infosys (INFY.NS)": "INFY.NS",
        "ICICI Bank (ICICIBANK.NS)": "ICICIBANK.NS",
        "SBI (SBIN.NS)": "SBIN.NS",
        "ITC (ITC.NS)": "ITC.NS",
        "Larsen & Toubro (LT.NS)": "LT.NS",
        "Bharti Airtel (BHARTIARTL.NS)": "BHARTIARTL.NS",
        "Tata Motors (TATAMOTORS.NS)": "TATAMOTORS.NS",
    },
    "US — Indices & ETFs": {
        "S&P 500 (^GSPC)": "^GSPC",
        "Nasdaq Composite (^IXIC)": "^IXIC",
        "Dow Jones (^DJI)": "^DJI",
        "SPY ETF (SPY)": "SPY",
        "QQQ ETF (QQQ)": "QQQ",
    },
    "US — Stocks": {
        "Apple (AAPL)": "AAPL",
        "Microsoft (MSFT)": "MSFT",
        "Alphabet (GOOGL)": "GOOGL",
        "Amazon (AMZN)": "AMZN",
        "NVIDIA (NVDA)": "NVDA",
        "Tesla (TSLA)": "TSLA",
        "Meta (META)": "META",
    },
    "Crypto": {
        "Bitcoin (BTC-USD)": "BTC-USD",
        "Ethereum (ETH-USD)": "ETH-USD",
        "Solana (SOL-USD)": "SOL-USD",
    },
    "Commodities & FX": {
        "Gold Futures (GC=F)": "GC=F",
        "Crude Oil (CL=F)": "CL=F",
        "USD/INR (INR=X)": "INR=X",
    },
}

# Flat dict kept for backwards compatibility / direct lookup
POPULAR_TICKERS: dict[str, str] = {
    label: symbol
    for group in TICKERS_BY_MARKET.values()
    for label, symbol in group.items()
}


# ---------------------------------------------------------------------------
# Market detection — used to pick a sensible risk-free rate per asset class
# ---------------------------------------------------------------------------

# Annual risk-free rates per asset class (used in Sharpe denominator).
# Sources: 10Y govt bond yields (approx), crypto/commodities use 0 by convention.
MARKET_RISK_FREE_RATES: dict[str, float] = {
    "india": 0.07,
    "us": 0.045,
    "crypto": 0.0,
    "commodity": 0.045,
    "fx": 0.045,
    "other": 0.045,
}

# Display currency per market (used for ₹ vs $ formatting hints)
MARKET_CURRENCY: dict[str, str] = {
    "india": "₹",
    "us": "$",
    "crypto": "$",
    "commodity": "$",
    "fx": "",
    "other": "$",
}


def detect_market(ticker: str) -> str:
    """
    Classify a Yahoo Finance ticker into a market bucket.

    Returns one of: 'india', 'us', 'crypto', 'commodity', 'fx', 'other'.
    """
    t = ticker.upper().strip()
    if t.endswith(".NS") or t.endswith(".BO") or t in {"^NSEI", "^BSESN", "^NSEBANK"}:
        return "india"
    if t.endswith("-USD") or t.endswith("-USDT"):
        return "crypto"
    if t.endswith("=X"):
        return "fx"
    if t.endswith("=F"):
        return "commodity"
    if t in {"^GSPC", "^IXIC", "^DJI", "^RUT", "^VIX"} or t.isalpha():
        return "us"
    return "other"


def market_risk_free_rate(ticker: str) -> float:
    """Return the annualized risk-free rate appropriate for the ticker's market."""
    return MARKET_RISK_FREE_RATES[detect_market(ticker)]


def market_currency(ticker: str) -> str:
    """Return the display currency symbol for the ticker's market."""
    return MARKET_CURRENCY[detect_market(ticker)]


# ---------------------------------------------------------------------------
# Core fetch function — cached by (ticker, start, end)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner="Fetching market data...")
def fetch_ohlcv(ticker: str, start: str, end: str) -> pd.DataFrame:
    """
    Fetch historical OHLCV data for a given ticker and date range.

    Parameters
    ----------
    ticker : str
        Yahoo Finance ticker symbol (e.g. '^NSEI', 'AAPL', 'RELIANCE.NS')
    start  : str
        Start date in 'YYYY-MM-DD' format
    end    : str
        End date in 'YYYY-MM-DD' format

    Returns
    -------
    pd.DataFrame
        DataFrame with DatetimeIndex and columns [Open, High, Low, Close, Volume].
        All NaN rows filled forward then remaining NaNs dropped.

    Raises
    ------
    ValueError
        If the ticker is invalid or no data is returned for the given range.
    """
    try:
        raw = yf.download(
            ticker,
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
        )
    except Exception as exc:
        raise ValueError(f"yfinance error for '{ticker}': {exc}") from exc

    if raw is None or raw.empty:
        raise ValueError(
            f"No data returned for ticker '{ticker}' between {start} and {end}. "
            "Check the ticker symbol or try a different date range."
        )

    # Flatten multi-level columns that yfinance sometimes returns
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    # Keep only OHLCV columns
    keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in raw.columns]
    df = raw[keep].copy()

    # Fill forward (market holidays) then drop any remaining NaNs
    df = df.ffill().dropna()

    if df.empty:
        raise ValueError(
            f"Data for '{ticker}' was empty after cleaning. Try a wider date range."
        )

    df.index = pd.to_datetime(df.index)
    return df


def validate_date_range(start: str, end: str, min_days: int = 60) -> None:
    """
    Raise ValueError if the date range is too narrow for meaningful backtesting.
    """
    delta = (pd.Timestamp(end) - pd.Timestamp(start)).days
    if delta < min_days:
        raise ValueError(
            f"Date range is only {delta} days. Please select at least {min_days} days "
            "to generate meaningful signals."
        )
    if pd.Timestamp(end) <= pd.Timestamp(start):
        raise ValueError("End date must be after start date.")
