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

POPULAR_TICKERS = {
    "Nifty 50 (^NSEI)": "^NSEI",
    "BSE Sensex (^BSESN)": "^BSESN",
    "Reliance (RELIANCE.NS)": "RELIANCE.NS",
    "TCS (TCS.NS)": "TCS.NS",
    "HDFC Bank (HDFCBANK.NS)": "HDFCBANK.NS",
    "Infosys (INFY.NS)": "INFY.NS",
    "S&P 500 (^GSPC)": "^GSPC",
    "SPY ETF (SPY)": "SPY",
    "Apple (AAPL)": "AAPL",
    "Bitcoin (BTC-USD)": "BTC-USD",
}


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
